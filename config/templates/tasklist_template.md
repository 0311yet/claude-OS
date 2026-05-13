# Task List Template

This file shows the expected format for tasklist.md. The Planner agent should follow this structure.

---

# Task List

Generated from: .claude-os/PRD.md
Date: YYYY-MM-DD

## Phase 1: Project Setup

- [ ] #1 Initialize project with {framework}            blockedBy: none  files: package.json, src/index.js
- [ ] #2 Set up project structure (directories, configs)  blockedBy: #1  files: src/config.js, .env.example
- [ ] #3 Configure database and models                    blockedBy: #2  files: src/db.js, src/models/

## Phase 2: Core Feature — {Feature Name}

- [ ] #4 Implement {specific feature component}           blockedBy: #3  files: src/routes/users.js
- [ ] #5 Implement {specific feature component}           blockedBy: #3  files: src/routes/auth.js
- [ ] #6 Write tests for {feature}                        blockedBy: #4, #5  files: tests/users.test.js, tests/auth.test.js

## Phase 3: {Next Feature}

- [ ] #7 ...                                              blockedBy: ...  files: ...
- [ ] #8 ...                                              blockedBy: ...  files: ...

## Phase 4: Polish & Testing

- [ ] #9 Integration testing                              blockedBy: #6, #8  files: tests/integration/
- [ ] #10 README and documentation                        blockedBy: none  files: README.md

---

## Status Legend

- `[ ]` — Pending (not started)
- `[IN_PROGRESS]` — Currently being worked on
- `[DONE]` — Completed
- `[BLOCKED]` — Failed after max retries, needs user attention

## blockedBy Format

- `none` — No dependencies, can start immediately
- `#3` — Depends on task #3 being DONE
- `#3, #5` — Depends on both #3 AND #5 being DONE

## files Format

- Lists files that this task will create or modify
- Used by Leader to detect conflicts when assigning parallel tasks
- If two tasks share a file, they must be assigned to the same Developer
- Can use directory paths (ending with /) when multiple files in a directory will be touched
