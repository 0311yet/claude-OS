# ClaudeOS

Claude Code 生命周期管理器。自动启动、监控、重启 Claude Code 会话，支持无人值守的项目开发。

## 它做什么

```
Orchestrator ──启动──▶ Claude Code 会话
   │                        │
   ├── 监控 state.json ◀─── 更新状态（turn/status）
   ├── 超时/心跳检测         │
   └── 自动重启 ◀─── 会话结束 ─── 恢复上下文
```

**Orchestrator** 是一个单文件 Python 脚本，负责：

- 初始化工作区（git、skills、state.json）
- 启动 Claude Code（`--dangerously-skip-permissions`）
- 通过 state.json 监控会话状态
- 超时（1.5h）/ 心跳（40min）/ 异常退出自动重启
- 重启时通过 recovery_context 恢复上下文

**Claude Code** 是实际的工作者，负责探索项目、写代码、跑测试。它通过更新 state.json 与 orchestrator 通信。

## 快速开始

### 一键安装（添加 `cos` 到 PATH）

```bat
install.bat
```

之后在任意文件夹地址栏输入 `cos` 即可启动。

### 手动使用

```bash
python orchestrator.py /path/to/project
```

## 前置条件

- Python 3.10+
- Claude Code CLI（`claude`）
- Git

## 状态管理

Claude Code 通过 `.claude-os/state.json` 与 orchestrator 通信：

| 字段 | 谁写入 | 说明 |
|------|--------|------|
| `status` | Claude | `running` / `idle` / `restarting` |
| `turn` | Claude | 每完成一个重要步骤 +1 |
| `recovery_context` | Claude | 会话结束前的进度摘要，供下次重启恢复 |
| `restart_count` | Orchestrator | 当前重启次数 |
| `total_sessions` | Orchestrator | 总会话数 |

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CLAUDEOS_TIMEOUT` | 5400 | 会话超时（秒） |
| `CLAUDEOS_HEARTBEAT` | 2400 | 心跳超时（秒） |
| `CLAUDEOS_IDLE_TIMEOUT` | 600 | idle 状态超时（秒） |

## 项目结构

```
claude-OS/
├── orchestrator.py              # 入口：初始化 + 启动/监控/重启
├── status_helper.py             # 标题栏状态显示（后台进程）
├── cos.cmd                      # Windows 地址栏启动器
├── install.bat                  # 一键 PATH 安装
├── config/
│   └── skills/
│       └── ui-ux-pro-max/      # 内置 UI/UX 设计技能
└── README.md
```

## 内置 Skills

ClaudeOS 内置 [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) 技能，在初始化时自动安装到项目的 `.claude/skills/` 目录。Claude Code 会在需要时自动调用，提供设计系统、配色方案、排版等建议。

## License

MIT
