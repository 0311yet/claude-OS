"""
ClaudeOS Orchestrator - Multi-agent development framework

Usage:
    python orchestrator.py [workspace_dir]

If workspace_dir is not provided, defaults to ./project/ relative to the orchestrator script.
"""

import json
import os
import re
import sys
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from contextlib import contextmanager

try:
    import ctypes
    from ctypes import wintypes
except ImportError:
    ctypes = None

CONFIG_DIR = Path(__file__).parent / "config"

# .claude-os directory files
RESTART_STATE_FILE = "restart_state"
RECOVERY_FILE = "recovery.md"

# Restart state values (written to restart_state file)
STATE_RUNNING = "running"
STATE_IDLE = "idle"
STATE_PLEASE_RESTART = "please_restart"
STATE_READY = "ready"

# Session timeout: configurable via CLAUDEOS_TIMEOUT env var (seconds), default 1 hour
SESSION_TIMEOUT_SECONDS = int(os.environ.get("CLAUDEOS_TIMEOUT", "5400"))
# Fallback force-kill timeout after writing "please_restart" (seconds)
PLEASE_RESTART_TIMEOUT = 900
# Heartbeat: if log.md mtime is older than this (seconds) while running, treat as stuck
HEARTBEAT_TIMEOUT = int(os.environ.get("CLAUDEOS_HEARTBEAT", "2400"))
MAX_RESTARTS = 8
POLL_INTERVAL = 10
POLL_INTERVAL_IDLE = 60


GITIGNORE_ENTRIES = [
    ".claude-os/restart_state",
    ".claude-os/recovery.md",
    ".claude-os/log.md",
    ".claude/CLAUDE.md.bak",
    ".claude/settings.json",
    "config/secrets.json",
    "node_modules/",
    "__pycache__/",
    ".env",
]


def _ensure_gitignore(workspace: Path):
    """Create .gitignore if missing, or merge missing entries into existing one."""
    gitignore = workspace / ".gitignore"
    header = "# Auto-managed by ClaudeOS — safe to add your own entries below\n"

    if not gitignore.exists():
        gitignore.write_text(header + "\n".join(GITIGNORE_ENTRIES) + "\n", encoding="utf-8")
        print(f"  Created {gitignore}")
        return

    try:
        existing = gitignore.read_text(encoding="utf-8")
    except OSError:
        return

    existing_lines = set(line.strip() for line in existing.splitlines())
    missing = [e for e in GITIGNORE_ENTRIES if e not in existing_lines]
    if missing:
        with open(gitignore, "a", encoding="utf-8") as f:
            f.write("\n# ClaudeOS additions\n")
            for entry in missing:
                f.write(entry + "\n")
        print(f"  Updated .gitignore with {len(missing)} missing entries")


def setup_workspace(workspace: Path):
    """Set up workspace with CLAUDE.md, agent definitions, skills, and templates."""
    claude_dir = workspace / ".claude"
    agents_dir = claude_dir / "agents"
    claude_os_dir = workspace / ".claude-os"

    # Create directories
    agents_dir.mkdir(parents=True, exist_ok=True)
    claude_os_dir.mkdir(parents=True, exist_ok=True)

    # Initialize git repository if not already one
    git_dir = workspace / ".git"
    if not git_dir.exists():
        subprocess.run(["git", "init"], cwd=str(workspace), capture_output=True)
        print(f"  Initialized git repository")
        result = subprocess.run(
            ["git", "config", "user.email"],
            cwd=str(workspace), capture_output=True, text=True,
        )
        if not result.stdout.strip():
            subprocess.run(
                ["git", "config", "user.email", "claude-os@local"],
                cwd=str(workspace), capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "ClaudeOS"],
                cwd=str(workspace), capture_output=True,
            )
            print(f"  Configured local git user")
    else:
        print(f"  Git repository already exists")

    # Copy Leader instructions -> .claude/CLAUDE.md
    leader_src = CONFIG_DIR / "leader.md"
    leader_dst = claude_dir / "CLAUDE.md"
    if leader_dst.exists():
        backup = claude_dir / "CLAUDE.md.bak"
        shutil.copy2(leader_dst, backup)
        print(f"  Backed up existing CLAUDE.md -> {backup}")
    shutil.copy2(leader_src, leader_dst)
    print(f"  Created {leader_dst}")

    # Copy agent definitions -> .claude/agents/
    agent_files = ["planner.md", "developer.md", "tester.md"]
    for agent_file in agent_files:
        src = CONFIG_DIR / "agents" / agent_file
        dst = agents_dir / agent_file
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  Created {dst}")
        else:
            print(f"  WARNING: Missing agent file: {src}")

    # Install bundled skills -> .claude/skills/
    _install_skills(claude_dir)

    # Create or update .gitignore
    _ensure_gitignore(workspace)

    # Create empty state files if they don't exist
    state_files = {
        "session-memory.md": "# Session Memory\n\nLast updated: —\nTotal sessions: 0\n\n## Project Overview\n\n## Key Architecture Decisions\n\n## User Preferences\n\n## Known Issues & Workarounds\n\n## What Works Well\n\n## What to Avoid\n\n## Next Steps\n\n",
        "PRD.md": "# Product Requirements Document\n\n",
        "tasklist.md": "# Task List\n\n",
        "progress.md": "# Development Progress\n\n",
    }
    for filename, default_content in state_files.items():
        filepath = claude_os_dir / filename
        if not filepath.exists():
            filepath.write_text(default_content, encoding="utf-8")
            print(f"  Created {filepath}")

    # Create log file if it doesn't exist
    log_file = claude_os_dir / "log.md"
    if not log_file.exists():
        log_file.write_text("# ClaudeOS Operation Log\n\n", encoding="utf-8")
        print(f"  Created {log_file}")

    # Clean stale restart signal (legacy) and initialize restart_state
    legacy_signal = claude_os_dir / "restart_signal"
    if legacy_signal.exists():
        legacy_signal.unlink()
    state_file = claude_os_dir / RESTART_STATE_FILE
    if not state_file.exists():
        state_file.write_text(STATE_RUNNING, encoding="utf-8")
        print(f"  Initialized {state_file}")

    # Configure MCP servers
    _setup_mcp_servers(claude_dir, workspace)


def _install_skills(claude_dir: Path):
    """Copy bundled skills from config/skills/ to .claude/skills/."""
    skills_src = CONFIG_DIR / "skills"
    if not skills_src.exists():
        return

    skills_dst = claude_dir / "skills"
    skills_dst.mkdir(parents=True, exist_ok=True)

    for skill_dir in skills_src.iterdir():
        if not skill_dir.is_dir():
            continue
        dst = skills_dst / skill_dir.name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(skill_dir, dst)
        print(f"  Installed skill: {skill_dir.name}")


def _setup_mcp_servers(claude_dir: Path, workspace: Path):
    """Read config/mcp.json, resolve variables, install deps, write to settings.json."""
    mcp_config_file = CONFIG_DIR / "mcp.json"

    if not mcp_config_file.exists():
        print("  No config/mcp.json found — skipping MCP server setup.")
        return

    try:
        mcp_config = json.loads(mcp_config_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"  WARNING: Could not read config/mcp.json: {e}")
        return

    new_servers = mcp_config.get("mcpServers")
    if not new_servers:
        print("  config/mcp.json has no mcpServers — skipping.")
        return

    secrets = _load_secrets()

    config_dir_abs = str(CONFIG_DIR.resolve())
    workspace_dir_abs = str(workspace.resolve())
    resolved_servers = {}
    for name, server_conf in new_servers.items():
        resolved_servers[name] = _resolve_vars(server_conf, config_dir_abs, secrets, workspace_dir_abs)

    _validate_mcp_servers(resolved_servers)
    _install_mcp_deps()

    settings_file = claude_dir / "settings.json"

    if settings_file.exists():
        try:
            existing = json.loads(settings_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"  WARNING: Could not read {settings_file}: {e}")
            return

        if "mcpServers" not in existing:
            existing["mcpServers"] = {}

        existing["mcpServers"].update(resolved_servers)
    else:
        existing = {"mcpServers": dict(resolved_servers)}

    _atomic_write(settings_file, json.dumps(existing, indent=2, ensure_ascii=False) + "\n")

    server_names = ", ".join(resolved_servers.keys())
    print(f"  Configured MCP servers: {server_names}")


def _load_secrets():
    """Load API keys from config/secrets.json."""
    secrets_file = CONFIG_DIR / "secrets.json"
    if not secrets_file.exists():
        print("\n  [SETUP REQUIRED] config/secrets.json not found.")
        print("  Copy config/secrets.example.json to config/secrets.json and fill in your API keys.\n")
        return {}

    try:
        raw = json.loads(secrets_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"  WARNING: Could not read config/secrets.json: {e}")
        return {}

    if not isinstance(raw, dict):
        print("  WARNING: config/secrets.json must be a JSON object {\"KEY\": \"value\"}.")
        return {}

    secrets = {}
    empty_keys = []
    for key, value in raw.items():
        if isinstance(value, str):
            secrets[key] = value
            if not value:
                empty_keys.append(key)
        elif value is None or value == "":
            secrets[key] = ""
            empty_keys.append(key)
        else:
            print(f"  WARNING: secrets.{key} has non-string value ({type(value).__name__}), skipping.")

    key_count = sum(1 for v in secrets.values() if v)
    print(f"  Loaded {key_count} API key(s) from config/secrets.json")

    if empty_keys:
        print(f"  NOTE: {len(empty_keys)} key(s) not configured: {', '.join(empty_keys)}")

    return secrets


def _resolve_vars(obj, config_dir, secrets=None, workspace_dir=None):
    """Recursively resolve ${configDir}, ${workspaceDir}, and ${secrets.XXX} in all string values."""
    if isinstance(obj, str):
        result = obj.replace("${configDir}", config_dir)
        if workspace_dir:
            result = result.replace("${workspaceDir}", workspace_dir)
        if secrets:
            for match in re.finditer(r'\$\{secrets\.(\w+)\}', result):
                key = match.group(1)
                if key in secrets and secrets[key]:
                    result = result.replace(match.group(0), str(secrets[key]))
                else:
                    print(f"  WARNING: secrets.{key} not found or empty in config/secrets.json")
                    result = result.replace(match.group(0), "")
        return result
    if isinstance(obj, list):
        return [_resolve_vars(item, config_dir, secrets, workspace_dir) for item in obj]
    if isinstance(obj, dict):
        return {k: _resolve_vars(v, config_dir, secrets, workspace_dir) for k, v in obj.items()}
    return obj


def _validate_mcp_servers(servers):
    """Check that MCP server scripts exist at resolved paths."""
    for name, conf in servers.items():
        if not isinstance(conf, dict):
            continue
        command = conf.get("command", "")
        args = conf.get("args", [])
        if command in ("node", "python") and args:
            script_path = Path(args[0])
            if not script_path.exists():
                print(f"  WARNING: MCP server '{name}' script not found: {args[0]}")


def _atomic_write(filepath, content):
    """Write file atomically: write to temp file, then replace."""
    filepath = Path(filepath)
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(
            dir=str(filepath.parent),
            prefix=".tmp_",
            suffix=".json",
        )
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, str(filepath))
        tmp_path = None
    except OSError as e:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        print(f"  WARNING: Failed to write {filepath}: {e}")


def _install_mcp_deps():
    """Install npm dependencies for custom MCP servers."""
    mcp_servers_dir = CONFIG_DIR / "mcp_servers"
    if not mcp_servers_dir.exists():
        return

    for server_dir in mcp_servers_dir.iterdir():
        if not server_dir.is_dir():
            continue

        pkg_json = server_dir / "package.json"
        node_modules = server_dir / "node_modules"
        if pkg_json.exists() and not node_modules.exists():
            print(f"  Installing MCP server deps: {server_dir.name}...")
            result = subprocess.run(
                ["npm", "install", "--production"],
                cwd=str(server_dir),
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print(f"    {server_dir.name} deps installed.")
            else:
                print(f"    WARNING: npm install failed for {server_dir.name}:")
                print(f"    {result.stderr.strip()[:200]}")


def _print_banner(workspace: Path, restarting=False):
    print(f"\n{'='*55}")
    if restarting:
        print("  ClaudeOS - Restarted (context recovered)")
    else:
        print("  ClaudeOS - Multi-Agent Development Framework")
    print(f"  Workspace: {workspace}")
    print(f"{'='*55}\n")


# Valid tool names that Claude Code recognizes
VALID_TOOLS = {
    "Read", "Write", "Edit", "Bash", "Glob", "Grep",
    "WebSearch", "WebFetch", "NotebookEdit",
}

REQUIRED_AGENT_FIELDS = {"name", "description", "tools"}
REQUIRED_AGENTS = ["planner.md", "developer.md", "tester.md"]


def validate_config():
    """Validate all config files before starting. Returns True if OK."""
    errors = []

    # Check leader.md exists
    leader_file = CONFIG_DIR / "leader.md"
    if not leader_file.exists():
        errors.append(f"Missing leader instructions: {leader_file}")
    else:
        content = leader_file.read_text(encoding="utf-8")
        if not content.strip():
            errors.append(f"Leader instructions are empty: {leader_file}")

    # Check each agent file
    agents_dir = CONFIG_DIR / "agents"
    for agent_file in REQUIRED_AGENTS:
        agent_path = agents_dir / agent_file
        if not agent_path.exists():
            errors.append(f"Missing agent definition: {agent_path}")
            continue

        content = agent_path.read_text(encoding="utf-8")
        if not content.strip():
            errors.append(f"Agent file is empty: {agent_path}")
            continue

        match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if not match:
            errors.append(f"No frontmatter found in: {agent_path}")
            continue

        frontmatter_text = match.group(1)

        if '\t' in frontmatter_text:
            errors.append(f"Tab characters in frontmatter (use spaces): {agent_path}")

        fields = {}
        for line in frontmatter_text.split('\n'):
            line = line.strip()
            if ':' in line and not line.startswith('-'):
                key, _, value = line.partition(':')
                fields[key.strip()] = value.strip()

        tools_match = re.search(r'tools:\s*\n((?:\s*-\s*\w+\s*\n?)+)', frontmatter_text)
        if tools_match:
            tool_list = re.findall(r'-\s*(\w+)', tools_match.group(1))
            fields['tools'] = tool_list

        for field in REQUIRED_AGENT_FIELDS:
            if field not in fields:
                errors.append(f"Missing '{field}' in frontmatter: {agent_path}")

        if 'tools' in fields and isinstance(fields['tools'], list):
            for tool in fields['tools']:
                if tool not in VALID_TOOLS:
                    errors.append(f"Unknown tool '{tool}' in {agent_path}")

    if errors:
        print("\n[Validation Errors]")
        for err in errors:
            print(f"  X {err}")
        print()
        return False

    print("  Config validation passed")
    return True


def _reset_windows_console():
    """Reset Windows console modes to prevent garbled display/input.

    Claude Code (or any interactive CLI) modifies console modes (raw input,
    ANSI processing). When the orchestrator kills the Leader process, these
    modes aren't restored, causing garbled display and broken keyboard input.
    This function resets both stdin and stdout to safe defaults.
    """
    if sys.platform != "win32" or ctypes is None:
        return
    try:
        kernel32 = ctypes.windll.kernel32
        STD_INPUT_HANDLE = -10
        STD_OUTPUT_HANDLE = -11

        # Reset stdin: ENABLE_PROCESSED_INPUT | ENABLE_LINE_INPUT | ENABLE_ECHO_INPUT | ENABLE_VIRTUAL_TERMINAL_INPUT
        h = kernel32.GetStdHandle(STD_INPUT_HANDLE)
        if h and h not in (0, ctypes.c_void_p(-1).value):
            mode = wintypes.DWORD()
            if kernel32.GetConsoleMode(h, ctypes.byref(mode)):
                kernel32.SetConsoleMode(h, 0x0001 | 0x0002 | 0x0004 | 0x0200)

        # Reset stdout: ENABLE_PROCESSED_OUTPUT | ENABLE_WRAP_AT_EOL_OUTPUT | ENABLE_VIRTUAL_TERMINAL_PROCESSING
        h = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        if h and h not in (0, ctypes.c_void_p(-1).value):
            mode = wintypes.DWORD()
            if kernel32.GetConsoleMode(h, ctypes.byref(mode)):
                kernel32.SetConsoleMode(h, 0x0001 | 0x0002 | 0x0004)
    except Exception:
        pass


class Orchestrator:
    """Manages the Leader CLI process lifecycle with context monitoring."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.claude_os_dir = workspace / ".claude-os"
        self.state_file = self.claude_os_dir / RESTART_STATE_FILE
        self.recovery_file = self.claude_os_dir / RECOVERY_FILE
        self.log_file = self.claude_os_dir / "log.md"
        self.leader_process = None
        self.running = False
        self.leader_start_time = None
        self.please_restart_time = None
        self.restart_count = 0
        self.session_log_mtime = None
        self._lock = threading.Lock()

    def _start_leader(self, initial_prompt=None):
        """Launch Claude Code CLI as the Leader session."""
        _reset_windows_console()  # ensure clean console before launch
        try:
            cmd = ["claude", "--dangerously-skip-permissions"]
            if initial_prompt:
                cmd.append(initial_prompt)
            kwargs = {"cwd": str(self.workspace)}
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            with self._lock:
                self.leader_process = subprocess.Popen(cmd, **kwargs)
                self.leader_start_time = time.time()
                self.timeout_triggered = False
                self.session_log_mtime = None
        except FileNotFoundError:
            print("Error: 'claude' CLI not found. Please install Claude Code first.")
            print("  https://docs.anthropic.com/en/docs/claude-code")
            sys.exit(1)
        except PermissionError:
            print("Error: Permission denied when starting 'claude' CLI.")
            sys.exit(1)
        except OSError as e:
            print(f"Error: Failed to start Claude CLI: {e}")
            sys.exit(1)

    def _stop_leader(self):
        """Stop the Leader process."""
        with self._lock:
            if self.leader_process is None:
                return
            if self.leader_process.poll() is not None:
                return
            self.leader_process.terminate()

        try:
            self.leader_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                self.leader_process.kill()
                self.leader_process.wait(timeout=3)
            except (OSError, ProcessLookupError):
                pass

    def _verify_session_memory(self):
        """Check if session-memory.md was updated during this session."""
        memory_file = self.claude_os_dir / "session-memory.md"
        if not memory_file.exists():
            return

        memory_was_updated = False
        if self.leader_start_time and memory_file.exists():
            try:
                mtime = memory_file.stat().st_mtime
                memory_was_updated = mtime > self.leader_start_time
            except OSError:
                pass

        if memory_was_updated:
            print("[Orchestrator] Session memory verified — saved during this session.")
            return

        print("[Orchestrator] Warning: session-memory.md was NOT updated during this session.")
        print("[Orchestrator] Creating fallback memory from log.md...")

        fallback = self._build_fallback_memory()
        if fallback:
            existing = memory_file.read_text(encoding="utf-8")
            if "Total sessions: 0" in existing or not existing.strip():
                memory_file.write_text(fallback, encoding="utf-8")
                print("[Orchestrator] Fallback session memory written.")
            else:
                note = f"\n\n## Warning (auto-generated)\n\nSession ended {time.strftime('%Y-%m-%d %H:%M')} without memory update. Check log.md for details.\n"
                memory_file.write_text(existing + note, encoding="utf-8")

    def _build_fallback_memory(self):
        """Build a minimal session memory from log.md entries."""
        log_file = self.claude_os_dir / "log.md"
        if not log_file.exists():
            return None

        try:
            content = log_file.read_text(encoding="utf-8")
        except OSError:
            return None

        lines = [l.strip() for l in content.split('\n') if l.strip()]
        recent = lines[-20:] if len(lines) > 20 else lines

        return (
            "# Session Memory\n\n"
            f"Last updated: {time.strftime('%Y-%m-%d %H:%M')} (auto-generated fallback)\n"
            "Total sessions: 1\n\n"
            "## Note\n\n"
            "This memory was auto-generated because the Leader did not save session memory before exiting.\n"
            "The information below is extracted from log.md and may be incomplete.\n\n"
            "## Recent Activity\n\n"
            + '\n'.join(recent) + "\n"
        )

    def _read_state(self):
        """Read current restart_state value."""
        try:
            return self.state_file.read_text(encoding="utf-8").strip()
        except OSError:
            return STATE_RUNNING

    def _write_state(self, state):
        """Write state to restart_state file."""
        try:
            self.state_file.write_text(state, encoding="utf-8")
        except OSError as e:
            print(f"[Orchestrator] WARNING: Failed to write restart_state: {e}")

    def _monitor(self):
        """Background thread: poll restart_state file for cooperative restart."""
        prev_state = STATE_RUNNING
        while self.running:
            with self._lock:
                process = self.leader_process

            if process is None or process.poll() is not None:
                return

            state = self._read_state()

            if state == STATE_READY:
                print("\n[Orchestrator] Leader reports ready. Restarting...")
                self._stop_leader()
                return

            if state == STATE_PLEASE_RESTART:
                if self.please_restart_time is not None:
                    elapsed = time.time() - self.please_restart_time
                    if elapsed >= PLEASE_RESTART_TIMEOUT:
                        print(f"\n[Orchestrator] Leader did not respond to 'please_restart' within {PLEASE_RESTART_TIMEOUT}s. Force restarting...")
                        if not self.recovery_file.exists():
                            self.recovery_file.write_text(
                                "# Recovery State\n\n"
                                "## Current Phase\n"
                                "Unknown (force restart after unresponsive timeout)\n\n"
                                "## Conversation Summary\n"
                                "Leader did not respond to restart request within the fallback timeout.\n"
                                "Read .claude-os/PRD.md, .claude-os/tasklist.md, and .claude-os/progress.md to determine current state.\n",
                                encoding="utf-8",
                            )
                        self._stop_leader()
                        return

            elif state == STATE_IDLE:
                if self.please_restart_time is not None:
                    print("[Orchestrator] Leader went idle, cancelling restart request.")
                    self.please_restart_time = None
                if prev_state != STATE_IDLE:
                    print("[Orchestrator] Leader is idle. Timeout paused.")

            elif state == STATE_RUNNING:
                if prev_state == STATE_IDLE:
                    with self._lock:
                        self.leader_start_time = time.time()
                    print("[Orchestrator] Leader resumed from idle. Timeout reset.")

                with self._lock:
                    start_time = self.leader_start_time

                if start_time:
                    session_elapsed = time.time() - start_time
                    if session_elapsed >= SESSION_TIMEOUT_SECONDS:
                        print(f"\n[Orchestrator] Session timeout ({SESSION_TIMEOUT_SECONDS}s). Requesting graceful restart...")
                        self._write_state(STATE_PLEASE_RESTART)
                        self.please_restart_time = time.time()

                # Heartbeat check
                if self.log_file.exists():
                    try:
                        current_mtime = self.log_file.stat().st_mtime
                        if self.session_log_mtime is None:
                            if current_mtime > self.leader_start_time:
                                self.session_log_mtime = current_mtime

                        if self.session_log_mtime is not None:
                            log_age = time.time() - current_mtime
                            if log_age > HEARTBEAT_TIMEOUT:
                                print(f"\n[Orchestrator] Heartbeat lost — log.md not updated for {int(log_age)}s "
                                      f"(threshold: {HEARTBEAT_TIMEOUT}s). Requesting graceful restart...")
                                self._write_state(STATE_PLEASE_RESTART)
                                self.please_restart_time = time.time()
                    except OSError:
                        pass

            prev_state = state
            interval = POLL_INTERVAL_IDLE if state == STATE_IDLE else POLL_INTERVAL
            time.sleep(interval)

    def run(self):
        """Main loop: start Leader, monitor, restart when needed."""
        self.running = True
        first_run = True
        self.restart_count = 0

        while self.running:
            recovery_text = ""
            if self.recovery_file.exists():
                recovery_text = self.recovery_file.read_text(encoding="utf-8")

            is_restart = not first_run or bool(recovery_text)

            _print_banner(self.workspace, restarting=is_restart)

            if is_restart and recovery_text:
                print("[Orchestrator] Recovery state found. Session will resume.\n")

            self._write_state(STATE_RUNNING)
            self.please_restart_time = None

            if is_restart and recovery_text:
                initial_prompt = (
                    "You are the ClaudeOS Leader, resuming from a context restart. "
                    "Follow your instructions in order: 1) Read .claude-os/session-memory.md first, "
                    "2) Read .claude-os/recovery.md for recovery state, 3) Continue where the previous Leader left off. "
                    "IMPORTANT: Reset your turn counter to 0 — this is a fresh session."
                )
            else:
                initial_prompt = (
                    "You are the ClaudeOS Leader starting a fresh session. "
                    "Read .claude-os/session-memory.md first for accumulated context from previous sessions. "
                    "Start your turn counter at 0 and log [Turn X/15] for every action from the very beginning. Soft limit is 10, hard limit is 15."
                )

            self._start_leader(initial_prompt=initial_prompt)

            monitor = threading.Thread(target=self._monitor, daemon=True)
            monitor.start()

            try:
                self.leader_process.wait()
            except KeyboardInterrupt:
                print("\n\n[Orchestrator] Shutting down...")
                self._stop_leader()
                _reset_windows_console()
                self.running = False
                break

            exit_code = self.leader_process.returncode
            print(f"[Orchestrator] Leader exited with code {exit_code}")
            _reset_windows_console()  # clean up console after Leader exits

            self._verify_session_memory()

            final_state = self._read_state()

            should_restart = final_state == STATE_READY

            if not should_restart and exit_code != 0:
                print(f"[Orchestrator] Abnormal exit detected (code {exit_code}). Treating as restart...")
                should_restart = True
                if not self.recovery_file.exists():
                    self.recovery_file.write_text(
                        "# Recovery State\n\n"
                        "## Current Phase\n"
                        f"Unknown (Leader exited abnormally with code {exit_code})\n\n"
                        "## Conversation Summary\n"
                        f"Leader exited with code {exit_code}. "
                        "Read .claude-os/PRD.md, .claude-os/tasklist.md, and .claude-os/progress.md to determine current state.\n\n"
                        "## Important Context for Next Leader\n"
                        "The previous Leader session ended unexpectedly. Check log.md for details.\n",
                        encoding="utf-8",
                    )

            if should_restart:
                with self._lock:
                    self.restart_count += 1
                    count = self.restart_count
                if count >= MAX_RESTARTS:
                    print(f"\n[Orchestrator] Max restarts ({MAX_RESTARTS}) reached. Stopping.")
                    break

                delay = min(2 * (2 ** (count - 1)), 30)
                print(f"[Orchestrator] Restart #{count}/{MAX_RESTARTS} in {delay}s...\n")
                time.sleep(delay)
                first_run = False
                continue
            else:
                self.running = False

        print("\n[Orchestrator] Session ended.")


def main():
    if len(sys.argv) > 1:
        workspace = Path(sys.argv[1]).resolve()
    else:
        workspace = (Path(__file__).parent / "project").resolve()

    if not workspace.exists():
        print(f"Error: Workspace directory does not exist: {workspace}")
        sys.exit(1)

    print("Validating config...")
    if not validate_config():
        print("Fix config errors before starting.")
        sys.exit(1)

    print("\nSetting up ClaudeOS workspace...")
    setup_workspace(workspace)

    print("\nSetup complete.")

    orchestrator = Orchestrator(workspace)
    orchestrator.run()


if __name__ == "__main__":
    main()
