"""
ClaudeOS Orchestrator — Claude Code lifecycle manager.

Manages a single Claude Code session with auto-restart, state persistence,
and project-level skill installation.

Usage:
    python orchestrator.py [workspace_dir]
"""

import json
import os
import sys
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

try:
    import ctypes
except ImportError:
    ctypes = None

CONFIG_DIR = Path(__file__).parent / "config"

# Session parameters
SESSION_TIMEOUT_SECONDS = int(os.environ.get("CLAUDEOS_TIMEOUT", "5400"))
HEARTBEAT_TIMEOUT = int(os.environ.get("CLAUDEOS_HEARTBEAT", "2400"))
IDLE_TIMEOUT = int(os.environ.get("CLAUDEOS_IDLE_TIMEOUT", "600"))
MAX_RESTARTS = 8
POLL_INTERVAL = 10
POLL_INTERVAL_IDLE = 30

# State file values
STATUS_RUNNING = "running"
STATUS_IDLE = "idle"
STATUS_RESTARTING = "restarting"

GITIGNORE_ENTRIES = [
    ".claude-os/",
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".claude/CLAUDE.md.bak",
    "node_modules/",
    "__pycache__/",
    ".env",
]


# ── Console Fix ──────────────────────────────────────────────────────────────

def _reset_windows_console(force_screen_reset=False):
    if sys.platform != "win32" or ctypes is None:
        return
    try:
        kernel32 = ctypes.windll.kernel32
        STD_INPUT_HANDLE, STD_OUTPUT_HANDLE = -10, -11

        if force_screen_reset:
            for seq in ('\033[0m', '\033[r', '\033[H', '\033[2J'):
                sys.stdout.write(seq)
        else:
            for seq in ('\033[0m', '\033[K'):
                sys.stdout.write(seq)
        sys.stdout.flush()

        for handle_id, reset_mode in [
            (STD_INPUT_HANDLE, 0x0001 | 0x0002 | 0x0004 | 0x0200),
            (STD_OUTPUT_HANDLE, 0x0001 | 0x0002 | 0x0004),
        ]:
            h = kernel32.GetStdHandle(handle_id)
            if h and h not in (0, ctypes.c_void_p(-1).value):
                kernel32.SetConsoleMode(h, reset_mode)

        if force_screen_reset:
            sys.stdout.write('\033[H')
            sys.stdout.flush()
    except Exception:
        pass


# ── Workspace Setup ──────────────────────────────────────────────────────────

def _ensure_gitignore(workspace: Path):
    gitignore = workspace / ".gitignore"
    header = "# Auto-managed by ClaudeOS\n"
    if not gitignore.exists():
        gitignore.write_text(header + "\n".join(GITIGNORE_ENTRIES) + "\n", encoding="utf-8")
        return
    try:
        existing = set(line.strip() for line in gitignore.read_text(encoding="utf-8").splitlines())
    except OSError:
        return
    missing = [e for e in GITIGNORE_ENTRIES if e not in existing]
    if missing:
        with open(gitignore, "a", encoding="utf-8") as f:
            f.write("\n# ClaudeOS additions\n")
            for entry in missing:
                f.write(entry + "\n")


def _install_skills(claude_dir: Path):
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
        print(f"  已安装 skill: {skill_dir.name}")


def setup_workspace(workspace: Path):
    claude_dir = workspace / ".claude"
    os_dir = workspace / ".claude-os"

    claude_dir.mkdir(parents=True, exist_ok=True)
    os_dir.mkdir(parents=True, exist_ok=True)

    # Git init
    if not (workspace / ".git").exists():
        subprocess.run(["git", "init"], cwd=str(workspace), capture_output=True)
        result = subprocess.run(
            ["git", "config", "user.email"], cwd=str(workspace), capture_output=True, text=True,
        )
        if not result.stdout.strip():
            subprocess.run(["git", "config", "user.email", "claude-os@local"], cwd=str(workspace), capture_output=True)
            subprocess.run(["git", "config", "user.name", "ClaudeOS"], cwd=str(workspace), capture_output=True)
        print("  已初始化 git 仓库")

    # Install skills
    _install_skills(claude_dir)

    # .gitignore
    _ensure_gitignore(workspace)

    # Initialize state.json
    state_file = os_dir / "state.json"
    if not state_file.exists():
        state_file.write_text(json.dumps({
            "status": STATUS_RUNNING,
            "turn": 0,
            "restart_count": 0,
            "total_sessions": 1,
            "recovery_context": None,
        }, indent=2) + "\n", encoding="utf-8")
        print("  已初始化 state.json")


# ── Orchestrator ─────────────────────────────────────────────────────────────

class Orchestrator:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.os_dir = workspace / ".claude-os"
        self.state_file = self.os_dir / "state.json"
        self.claude_process = None
        self.running = False
        self.restart_count = 0
        self._lock = threading.Lock()
        self._system_start = None
        self._session_start = None
        self._status_helper = None
        self._completed_normally = False

    def _read_state(self):
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"status": STATUS_RUNNING, "recovery_context": None}

    def _write_state(self, **updates):
        try:
            state = json.loads(self.state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            state = {}
        state.update(updates)
        data = json.dumps(state, indent=2) + "\n"
        # Atomic write: write to temp file then replace
        fd, tmp = tempfile.mkstemp(dir=str(self.os_dir), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(data)
            os.replace(tmp, str(self.state_file))
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    def _start_status_helper(self):
        helper = Path(__file__).parent / "status_helper.py"
        if not helper.exists():
            return
        try:
            cmd = [sys.executable, str(helper), str(self.workspace)]
            kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            self._status_helper = subprocess.Popen(cmd, **kwargs)
        except Exception:
            pass

    def _stop_status_helper(self):
        if self._status_helper is None:
            return
        kill_file = self.os_dir / "status_kill"
        try:
            kill_file.write_text("1", encoding="utf-8")
        except OSError:
            pass
        try:
            self._status_helper.wait(timeout=5)
        except subprocess.TimeoutExpired:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(self._status_helper.pid)], capture_output=True)
            else:
                os.killpg(os.getpgid(self._status_helper.pid), 9)
        self._status_helper = None

    def _build_instructions(self):
        state = self._read_state()
        recovery = state.get("recovery_context")
        turn = state.get("turn", 0)

        template_path = CONFIG_DIR / "cos-instructions.md"
        try:
            template = template_path.read_text(encoding="utf-8")
        except OSError:
            template = "Read .claude-os/state.json for current state, then start working."

        if recovery:
            header = (
                f"**RECOVERY SESSION — Turn {turn}/15 (soft limit 10, hard limit 15)**\n\n"
                "Resume from the breakpoint below. Do NOT re-explore the entire project.\n"
                "Only read files needed for the immediate next step, then start working.\n\n"
                f"### Recovery Context\n\n{recovery}"
            )
        else:
            header = (
                f"**NEW SESSION — Turn {turn}/15 (soft limit 10, hard limit 15)**\n\n"
                "Quick overview: ls + 1-2 key files, then start working immediately.\n"
                "Do not do a full scan. Learn details as you go."
            )

        instructions = template.replace("{session_header}", header)
        instructions = instructions.replace("{turn_num}", str(turn))

        instructions_path = self.os_dir / "instructions.md"
        instructions_path.write_text(instructions, encoding="utf-8")
        return instructions_path

    def _start_claude(self, prompt):
        _reset_windows_console()
        cmd = ["claude", "--dangerously-skip-permissions", prompt]
        kwargs = {"cwd": str(self.workspace)}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        # Capture stderr to diagnose crash loops (exit code 1)
        log_file = self.os_dir / "claude_stderr.log"
        kwargs["stderr"] = open(log_file, "w", encoding="utf-8")
        try:
            with self._lock:
                self.claude_process = subprocess.Popen(cmd, **kwargs)
                self._session_start = time.time()
        except Exception as e:
            print(f"[Orchestrator] 启动 Claude 失败: {e}")
            self.claude_process = None

    def _stop_claude(self):
        with self._lock:
            if self.claude_process is None or self.claude_process.poll() is not None:
                return
            self.claude_process.terminate()
        _reset_windows_console()
        try:
            self.claude_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _reset_windows_console(force_screen_reset=True)
            try:
                self.claude_process.kill()
                self.claude_process.wait(timeout=3)
            except (OSError, ProcessLookupError):
                pass

    def _monitor(self):
        last_mtimes = {}
        idle_since = None
        last_state_mtime = None

        while self.running:
            with self._lock:
                proc = self.claude_process
            if proc is None or proc.poll() is not None:
                return

            state = self._read_state()
            status = state.get("status", STATUS_RUNNING)

            # Track state.json mtime to detect updates
            try:
                current_state_mtime = self.state_file.stat().st_mtime
            except OSError:
                current_state_mtime = 0

            if status == STATUS_RESTARTING:
                self._stop_claude()
                return

            if status == STATUS_IDLE:
                # Claude wrote idle — likely task done or waiting for input
                # If state.json was recently updated (Claude still writing), give it time
                if last_state_mtime is not None and current_state_mtime > last_state_mtime:
                    idle_since = time.time()  # Reset idle timer on state update
                    last_state_mtime = current_state_mtime
                elif idle_since is None:
                    idle_since = time.time()
                elif (time.time() - idle_since) > IDLE_TIMEOUT:
                    print(f"[Orchestrator] idle 超过 {IDLE_TIMEOUT}s，视为任务完成，退出")
                    self._completed_normally = True
                    self._stop_claude()
                    return
                time.sleep(POLL_INTERVAL_IDLE)
                continue

            # Reset idle tracking when status is running
            idle_since = None
            last_state_mtime = current_state_mtime

            # Session timeout
            with self._lock:
                session_start = self._session_start
            if session_start and (time.time() - session_start) >= SESSION_TIMEOUT_SECONDS:
                self._write_state(status=STATUS_RESTARTING)
                self._stop_claude()
                return

            # Heartbeat: check workspace mtime (any project file write counts)
            try:
                ws_mtime = self.workspace.stat().st_mtime
            except OSError:
                ws_mtime = 0
            last_mtimes.setdefault("workspace", ws_mtime)
            if ws_mtime > last_mtimes["workspace"]:
                last_mtimes["workspace"] = ws_mtime
            elif (time.time() - last_mtimes["workspace"]) > HEARTBEAT_TIMEOUT:
                self._write_state(status=STATUS_RESTARTING)
                self._stop_claude()
                return

            time.sleep(POLL_INTERVAL)

    def run(self):
        self.running = True
        self._system_start = time.time()
        self._start_status_helper()

        while self.running and self.restart_count < MAX_RESTARTS:
            is_restart = self.restart_count > 0
            print(f"\n{'='*55}")
            print(f"  ClaudeOS{' — 已重启' if is_restart else ''}")
            print(f"  工作区: {self.workspace}")
            print(f"{'='*55}\n")

            updates = {"status": STATUS_RUNNING, "turn": 0, "restart_count": self.restart_count}
            if is_restart:
                current = self._read_state()
                updates["total_sessions"] = current.get("total_sessions", 1) + 1
            self._write_state(**updates)
            self._build_instructions()
            self._start_claude("Read .claude-os/instructions.md and follow all instructions inside.")

            if self.claude_process is None:
                print("[Orchestrator] 无法启动 Claude，退出")
                self.running = False
                break

            monitor = threading.Thread(target=self._monitor, daemon=True)
            monitor.start()

            try:
                self.claude_process.wait()
            except KeyboardInterrupt:
                print("\n[Orchestrator] 正在关闭...")
                self._stop_status_helper()
                self._stop_claude()
                _reset_windows_console()
                self.running = False
                break

            exit_code = self.claude_process.returncode
            print(f"[Orchestrator] Claude 已退出，代码 {exit_code}")
            _reset_windows_console()

            # Show stderr on non-zero exit for diagnostics
            if exit_code != 0:
                stderr_log = self.os_dir / "claude_stderr.log"
                try:
                    stderr_content = stderr_log.read_text(encoding="utf-8").strip()
                    if stderr_content:
                        # Show last 20 lines max
                        lines = stderr_content.splitlines()
                        for line in lines[-20:]:
                            print(f"  [stderr] {line}")
                except OSError:
                    pass

            state = self._read_state()
            should_restart = (
                not self._completed_normally
                and (state.get("status") == STATUS_RESTARTING or exit_code != 0)
            )
            self._completed_normally = False

            if should_restart:
                self.restart_count += 1
                delay = min(2 * (2 ** (self.restart_count - 1)), 30)
                print(f"[Orchestrator] 第 {self.restart_count}/{MAX_RESTARTS} 次重启，{delay}秒后...")
                time.sleep(delay)
            else:
                self.running = False

        self._stop_status_helper()
        print("\n[Orchestrator] 会话已结束。")


def main():
    workspace = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else (Path(__file__).parent / "project").resolve()

    if not workspace.exists():
        print(f"错误：工作区不存在: {workspace}")
        sys.exit(1)

    print("\n正在初始化工作区...")
    setup_workspace(workspace)
    print("\n初始化完成。")

    Orchestrator(workspace).run()


if __name__ == "__main__":
    main()
