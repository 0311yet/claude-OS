# ClaudeOS State Protocol

MANDATORY. You MUST follow these rules. This is not optional.

## The One Rule

**Never exit on your own. Only the user (Ctrl+C) can stop you.**

- Have work → do it, track turns
- Turn limit reached → save progress, write `status: "restarting"`, exit (orchestrator will restart you)
- Work finished, no more tasks → wait for user input. Do NOT exit.
- Nothing to do → wait for user input. Do NOT exit.

## State File

Path: `.claude-os/state.json`

Read at session start to know your current turn.

## When to Update

Write FULL JSON via Bash (read → modify → tmp file → atomic replace):

```
python -c "
import json; s = json.load(open('.claude-os/state.json')); s['field'] = value
import tempfile, os
fd, tmp = tempfile.mkstemp(dir='.claude-os', suffix='.tmp')
with os.fdopen(fd, 'w') as f: json.dump(s, f, indent=2)
os.replace(tmp, '.claude-os/state.json')
"
```

| Event | Action |
|-------|--------|
| Start working | `status: "running"` |
| Complete a step | `turn + 1` |
| Turn limit reached | `recovery_context` + save memory + `status: "restarting"` → exit |
| Unrecoverable blocker | `recovery_context` + `status: "restarting"` → exit |

Do NOT write `status: "restarting"` for any other reason. If work is done but turn limit
hasn't been reached, wait for user input instead of exiting.

## Turn Limits

- Soft: 10 (stop starting new work, begin saving)
- Hard: 15 (must exit)
- At soft limit: finish current step → save → write `restarting` → exit
- Do NOT exit before turn limit unless blocked

## What "restarting" Means

`status: "restarting"` tells the orchestrator: "I hit the turn limit, restart me with fresh context."
Only write it when exiting due to turn limit or blocker.

## Recovery Context

Before exiting at turn limit, write `recovery_context` (under 500 words):
```
"Completed: X. Files: Y. Current state: Z. Next: W. Blockers: none."
```

## Language

- User communication: Chinese
- Code, comments, commits: English
