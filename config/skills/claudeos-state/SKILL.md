# ClaudeOS State Protocol

This is a MANDATORY behavioral protocol for sessions launched by ClaudeOS.
You MUST follow these rules in every turn. This is not optional.

## Core Rule

You are running in an unattended ClaudeOS session. No human is watching.
Before you exit, you MUST save all important context so the next session can continue.

## State File

Path: `.claude-os/state.json`

Read this file at the start of each significant action to know your current turn.

## When to Update

Write the FULL JSON (read → modify → write to tmp file → atomic replace) via Bash:

```
# Read, update, and atomically replace:
python -c "
import json
s = json.load(open('.claude-os/state.json'))
s['field'] = value
import tempfile, os
fd, tmp = tempfile.mkstemp(dir='.claude-os', suffix='.tmp')
with os.fdopen(fd, 'w') as f: json.dump(s, f, indent=2)
os.replace(tmp, '.claude-os/state.json')
"
```

| Event | What to write |
|-------|---------------|
| Start working | `status: "running"` |
| Complete an important step | `turn: turn + 1` |
| All work done | `recovery_context` + memory files + `status: "ready"`, then exit |
| Unrecoverable blocker | `status: "restarting"` |

NEVER set `status: "idle"`. This session is unattended.

## Turn Management

- Read current turn from state.json at session start
- Soft limit: 10 turns (recommended to finish)
- Hard limit: 15 turns (must stop)
- As you approach the soft limit, STOP starting new work and begin the completion sequence

## Completion Sequence (status → "ready")

When all work is done OR turn limit is approaching:

1. Write `recovery_context` to state.json — a concise summary of:
   - What was completed
   - What the current state is
   - What should happen next
   - Any blockers or gotchas
2. Save important context to memory files (if any cross-session knowledge was gained)
3. Write `status: "ready"` to state.json
4. Exit naturally

## Recovery Context Format

Keep it under 500 words. Factual, not narrative. Example:
```
"Completed: user auth module (JWT + bcrypt). Files: src/auth/*. Current: API routes working locally. Next: add refresh token rotation. Blocker: none. Note: .env needs JWT_SECRET set in production."
```

## Language

- Talk to user: Chinese
- Code, comments, commits, docs: English
