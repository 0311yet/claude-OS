"""ClaudeOS Status Helper — displays runtime status in title bar.

Launched by orchestrator.py as a background process.
Reads .claude-os/state.json for status info.
Exits when .claude-os/status_kill file appears.
"""

import json
import os
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    import ctypes


def format_duration(seconds):
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        m, s = divmod(int(seconds), 60)
        return f"{m}m{s:02d}s"
    h, remainder = divmod(int(seconds), 3600)
    m, _ = divmod(remainder, 60)
    return f"{h}h{m:02d}m"


def read_state(state_file):
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"turn": 0, "status": "-", "restart_count": 0}


def set_title(title):
    if sys.platform == "win32":
        try:
            ctypes.windll.kernel32.SetConsoleTitleW(title)
            return True
        except Exception:
            pass
    try:
        sys.stdout.write(f"\033]0;{title}\007")
        sys.stdout.flush()
        return True
    except (OSError, AttributeError):
        return False


def main():
    workspace = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    os_dir = workspace / ".claude-os"
    state_file = os_dir / "state.json"
    kill_file = os_dir / "status_kill"

    os_dir.mkdir(parents=True, exist_ok=True)

    if kill_file.exists():
        try:
            kill_file.unlink()
        except OSError:
            pass

    system_start = time.time()
    last_title = ""

    while True:
        if kill_file.exists():
            set_title("")
            try:
                kill_file.unlink()
            except OSError:
                pass
            return

        state = read_state(state_file)
        total = format_duration(time.time() - system_start)
        turns = state.get("turn", 0)
        restarts = state.get("restart_count", 0)
        status = state.get("status", "-")

        title = f"{total} | T{turns} R:{restarts} | {status}"
        if title != last_title:
            set_title(title)
            last_title = title

        time.sleep(3)


if __name__ == "__main__":
    main()
