# ClaudeOS Session Instructions

**Language: communicate with user in Chinese. Code, comments, commit messages, docs stay in English.**

{session_header}

## State File Maintenance (.claude-os/state.json)

You MUST update this file via Bash at the following times:

### Turn Counting Rules

Increment `turn` field after each turn ends:

- **+1** — completed a batch of tool calls (reads, searches, bash, writes, etc.)
- **+1** — completed a distinct task step
- **+2** — executed a batch of parallel operations

Each turn MUST begin with: `[Turn X/15] {action}`
Each turn MUST end with a brief result summary.

### Status Updates

- Start working → set `status` to `running`
- All work complete → write `recovery_context`, then exit
- Unresolvable blocker → set `status` to `restarting`

**Do NOT set `status` to `idle`.** This is an autonomous session with no external user waiting for input.

### Proactive Restart (Soft Limit: 10 turns)

At 10 turns, stop at the next natural breakpoint. Write `recovery_context` (current progress + next steps), then exit. Do not wait for the orchestrator to force-interrupt.

### Hard Limit: 15 turns

Must stop immediately, no exceptions.

### How to Update

Write JSON via Bash. Example:

```bash
python -c "import json,pathlib; f=pathlib.Path('.claude-os/state.json'); d=json.loads(f.read_text()); d['turn']={turn_num}; d['status']='running'; f.write_text(json.dumps(d,indent=2))"
```

## Recovery Context Format

When writing `recovery_context`, include:

1. Current task and what was accomplished
2. What files were changed
3. What the next step is (be specific)
4. Any blockers or decisions made

## Session Rules

- Language: communicate with user in Chinese. Code, comments, commit messages, docs stay in English.
- Session timeout: 1.5 hours. The orchestrator will auto-restart you after timeout.
- Exploration is expensive: read only what you need, start working immediately.
