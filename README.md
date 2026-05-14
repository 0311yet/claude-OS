# ClaudeOS

Multi-agent development framework powered by Claude Code. Orchestrates a team of AI agents (Leader, Planner, Developer, Tester) to build complete software projects autonomously.

## How It Works

```
User → Leader → Planner (plan)
                → Developer (code, parallel)
                → Tester (test)
```

The **Orchestrator** (Python) manages the Leader's lifecycle — start, monitor, restart on context overflow. The **Leader** (Claude Code) coordinates sub-agents, each spawned as an isolated Claude Code agent with clean context.

### Workflow Phases

| Phase | Description |
|-------|-------------|
| 1. Requirements | Leader gathers requirements from user, confirms tech stack |
| 2. Planning | Planner creates task breakdown with dependencies |
| 3. Development | Developers implement tasks in parallel (2-3 concurrent) |
| 4. Testing | Tester runs automated + manual + browser tests |
| 5. Delivery | Leader delivers summary to user |
| 6. Iteration | User requests changes → Developer → Tester loop |

## Prerequisites

- Python 3.10+
- Node.js + npm
- Claude Code CLI (`claude`)
- Git

## Installation

### Quick install (add `cos` to PATH)

Double-click `install.bat` or run in terminal:

```bat
install.bat
```

Then open any folder in Explorer, type `cos` in the address bar to start.

### Manual usage

```bash
python orchestrator.py /path/to/project
```

## Configuration

### API Keys

Copy the template and fill in your keys:

```bash
cp config/secrets.example.json config/secrets.json
```

Edit `config/secrets.json`:

```json
{
  "SERPAPI_API_KEY": ""            // Optional: web search
}
```

| Key | Required | Description |
|-----|----------|-------------|
| `SERPAPI_API_KEY` | No | SerpAPI for web search MCP |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDEOS_TIMEOUT` | 5400 | Leader session timeout (seconds) |
| `CLAUDEOS_HEARTBEAT` | 2400 | Heartbeat check interval (seconds) |

## Project Structure

```
claude-OS/
├── orchestrator.py              # Entry point: setup + start/monitor/restart
├── cos.cmd                      # Windows Explorer address bar launcher
├── install.bat                  # One-click PATH setup
├── requirements.txt             # Python deps (none required at top level)
├── config/
│   ├── leader.md                # Leader agent instructions
│   ├── mcp.json                 # MCP server declarations
│   ├── secrets.json             # API keys (gitignored)
│   ├── secrets.example.json     # API key template
│   ├── agents/
│   │   ├── planner.md           # Task breakdown agent
│   │   ├── developer.md         # Code implementation agent
│   │   └── tester.md            # Testing agent
│   ├── mcp_servers/
│   │   └── serpapi/             # Web search MCP (Node.js)
│   ├── skills/
│   │   └── ui-ux-pro-max/      # Bundled UI/UX design intelligence skill
│   │       ├── SKILL.md         # Skill instructions (auto-loaded by Claude Code)
│   │       ├── scripts/         # Search engine (BM25 + regex hybrid)
│   │       └── data/            # Design databases (styles, colors, fonts, etc.)
│   └── templates/
│       └── tasklist_template.md
└── README.md
```

## MCP Servers

ClaudeOS includes 2 MCP servers for extended capabilities:

| Server | Purpose | Auto-installed |
|--------|---------|----------------|
| **Playwright** | Browser automation for web testing | Yes (npx) |
| **SerpAPI** | Web search via Google | Yes (npm) |

Dependencies are auto-installed on first run.

## Bundled Skills

ClaudeOS includes the [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) skill, which provides AI-powered design intelligence for web and mobile applications:

- **67 UI styles** (glassmorphism, minimalism, brutalism, etc.)
- **161 color palettes** by product type
- **57 font pairings** with Google Fonts imports
- **99 UX guidelines** with severity ratings
- **25 chart types** with library recommendations
- **16 tech stacks** (React, Next.js, Vue, Svelte, etc.)

When the Developer agent builds UI pages, it automatically queries this skill for design system recommendations, color palettes, typography, and stack-specific best practices — ensuring production-quality visual design out of the box.

## Context Management

Claude Code has a finite context window. ClaudeOS handles this with:

- **Turn counter**: Each agent interaction increments the counter
- **Proactive restart**: At soft limit (10 turns), restart immediately via restart_state
- **Cooperative restart**: Leader saves state → writes `ready` → Orchestrator restarts
- **Heartbeat monitor**: If log.md goes stale for 40 minutes, force restart
- **Recovery**: New Leader reads recovery.md and resumes exactly where it left off

## License

MIT
