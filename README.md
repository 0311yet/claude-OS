# ClaudeOS

Claude Code 生命周期管理器。让 Claude Code 在无人值守环境下自主运行，自动处理会话管理、崩溃恢复和跨会话状态持久化。

## 工作原理

```
cos / python orchestrator.py [workspace]
│
├─ orchestrator.py    启动 Claude → 监控 state.json → 自动重启
├─ status_helper.py   Terminal title bar 显示运行状态
└─ config/skills/     状态协议 + UI/UX skill，自动安装到 .claude/skills/
```

Orchestrator 启动 Claude Code 子进程，通过 `state.json` 文件协议监控会话状态。Claude 完成工作后写 `status: "ready"` 正常退出；超时或崩溃时自动重启，通过 `recovery_context` 恢复上下文。

## 快速开始

```bash
# 安装 cos 命令到 PATH
install.bat

# 在任意项目目录启动
cos

# 或直接运行
python orchestrator.py /path/to/project
```

## 前置条件

- Python 3.10+
- Claude Code CLI（`claude`）
- Git

## 状态协议

Claude 通过 `.claude-os/state.json` 与 Orchestrator 通信：

| 状态 | 谁写 | 含义 |
|------|------|------|
| `running` | Orchestrator / Claude | 正在工作 |
| `ready` | Claude | 工作完成，记忆已保存 |
| `restarting` | Orchestrator / Claude | 遇到阻塞，需要重启 |

状态协议的完整规则在 `config/skills/claudeos-state/SKILL.md`，Orchestrator 启动时自动安装到项目的 `.claude/skills/` 目录。

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CLAUDEOS_TIMEOUT` | 5400 | 会话超时，秒（1.5h） |
| `CLAUDEOS_HEARTBEAT` | 2400 | 心跳超时，秒（40min） |

## 项目结构

```
claude-OS/
├── orchestrator.py                    # 核心管理器
├── status_helper.py                   # Title bar 状态显示
├── cos.cmd                            # Windows 地址栏启动器
├── install.bat                        # PATH 安装
├── config/skills/
│   ├── claudeos-state/                # 状态协议 skill
│   └── ui-ux-pro-max/                # UI/UX 设计 skill
└── README.md
```

## License

MIT
