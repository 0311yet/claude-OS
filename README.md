# ClaudeOS

Multi-agent development framework powered by Claude Code. Orchestrates a team of AI agents (Leader, Planner, Developer, Tester, Auditor) to build complete software projects autonomously.

## How It Works

```
User → Leader → Planner (plan)
                → Developer (code, parallel)
                → Tester (test)
                → Auditor (security audit)
```

The **Orchestrator** (Python) manages the Leader's lifecycle — start, monitor, restart on context overflow. The **Leader** (Claude Code) coordinates sub-agents, each spawned as an isolated Claude Code agent with clean context.

### Workflow Phases

| Phase | Description |
|-------|-------------|
| 1. Requirements | Leader gathers requirements from user, confirms tech stack |
| 2. Planning | Planner creates task breakdown with dependencies |
| 3. Development | Developers implement tasks in parallel (2-3 concurrent) |
| 3.5. Audit | Auditor performs security & quality review (optional) |
| 4. Testing | Tester runs automated + manual tests |
| 4.5. UI Testing | Dedicated Tester session with Playwright/vision tools |
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
  "SERPAPI_API_KEY": "",           // Optional: web search
  "VISION_PROVIDER": "zhipu",     // openai / gemini / zhipu
  "VISION_API_KEY": "",            // Required for UI testing
  "VISION_MODEL": "glm-4v-flash"  // Model name
}
```

| Key | Required | Description |
|-----|----------|-------------|
| `SERPAPI_API_KEY` | No | SerpAPI for web search MCP |
| `VISION_API_KEY` | Recommended | Vision analysis for UI testing. [ZhiPu](https://open.bigmodel.cn) glm-4v-flash has free tier |
| `VISION_PROVIDER` | No | Default `zhipu`. Options: `openai`, `gemini`, `zhipu` |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDEOS_TIMEOUT` | 3600 | Leader session timeout (seconds) |
| `CLAUDEOS_TESTER_TIMEOUT` | 7200 | Tester session timeout (seconds) |
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
│   ├── tester-session.md        # Tester session instructions (UI testing)
│   ├── mcp.json                 # MCP server declarations
│   ├── secrets.json             # API keys (gitignored)
│   ├── secrets.example.json     # API key template
│   ├── agents/
│   │   ├── planner.md           # Task breakdown agent
│   │   ├── developer.md         # Code implementation agent
│   │   ├── tester.md            # Testing agent
│   │   └── auditor.md           # Security audit agent (read-only)
│   ├── mcp_servers/
│   │   ├── serpapi/             # Web search MCP (Node.js)
│   │   ├── vision-analyzer/     # Visual analysis MCP (Python)
│   │   │   └── providers/       # OpenAI / Gemini / ZhiPu providers
│   │   └── computer-control/    # Desktop control MCP (Python, PyAutoGUI)
│   └── templates/
│       └── tasklist_template.md
└── README.md
```

## MCP Servers

ClaudeOS includes 4 MCP servers for extended capabilities:

| Server | Purpose | Auto-installed |
|--------|---------|----------------|
| **Playwright** | Browser automation for web testing | Yes (npx) |
| **SerpAPI** | Web search via Google | Yes (npm) |
| **Vision Analyzer** | Screenshot analysis via vision APIs | Yes (pip) |
| **Computer Control** | Desktop mouse/keyboard control | Yes (pip) |

Dependencies are auto-installed on first run.

## Context Management

Claude Code has a finite context window. ClaudeOS handles this with:

- **Turn counter**: Each agent interaction increments the counter
- **Proactive restart**: At soft limit (8 turns), restart at next natural breakpoint
- **Cooperative restart**: Leader saves state → writes `ready` → Orchestrator restarts
- **Heartbeat monitor**: If log.md goes stale for 40 minutes, force restart
- **Recovery**: New Leader reads recovery.md and resumes exactly where it left off

## License

MIT
