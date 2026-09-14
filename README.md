# Antigravity 2.0 Bridge

本项目将 Codex 与 macOS Antigravity 2.0 桌面版的本地 `agentapi` 连接方式分开封装为：

- `skills/antigravity-bridge/SKILL.md`：Codex 的使用规则和安全边界；
- `connector/antigravity_bridge.py`：独立的本地连接脚本。

## 安装 Skill

在本仓库根目录建立用户级软链接，使后续 Codex 会话能够发现 Skill：

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
ln -s "$PWD/skills/antigravity-bridge" "${CODEX_HOME:-$HOME/.codex}/skills/antigravity-bridge"
```

重新打开 Codex 会话后使用：

```text
使用 $antigravity-bridge，让 Antigravity 2.0 处理这个任务。
```

## 运作逻辑

1. 脚本定位 Antigravity 2.0 的本地 `language_server`，读取其 loopback 监听地址和运行时 CSRF 认证信息。
2. `doctor` 只检查本地 CLI、进程和监听端口，不访问任何会话。
3. `metadata` 只读取指定会话的元数据，用于确认连接，不代表任务完成。
4. `new` 通过 `new-conversation` 创建新会话；必须提供真实的 `project_id`，不能用对话 ID 或目录名代替。
5. `send` 通过 `send-message` 向明确指定的已有会话发送任务。
6. 默认是 dry-run，只显示将要执行的动作；只有明确附加 `--execute` 才会发送或创建。
7. 发送超时后状态视为未知，脚本不会自动重试，以避免重复执行任务。

认证令牌只在内存和子进程环境中传递，不写入文件，不放入命令行参数。任务内容禁止包含密码、API 密钥或其他机密信息。脚本只接受 loopback 地址，不修改 Antigravity 数据库、不改变权限、不自动审批，也不保证 headless 会话出现在桌面侧栏。

## 命令

```bash
python3 connector/antigravity_bridge.py --help
python3 connector/antigravity_bridge.py doctor
python3 connector/antigravity_bridge.py --pid <PID> metadata <CONVERSATION_ID>
python3 connector/antigravity_bridge.py --pid <PID> new --project-id <PROJECT_ID> --prompt-file <PROMPT_FILE>
python3 connector/antigravity_bridge.py --pid <PID> new --project-id <PROJECT_ID> --prompt-file <PROMPT_FILE> --execute
python3 connector/antigravity_bridge.py --pid <PID> send <CONVERSATION_ID> --prompt-file <PROMPT_FILE> --execute
```

PID、端口、项目 ID 和会话 ID 必须使用当前 Antigravity 2.0 实例中的真实值，示例中的尖括号内容不能直接照抄。
