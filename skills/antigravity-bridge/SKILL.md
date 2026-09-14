---
name: antigravity-bridge
description: Connect to the local Antigravity 2.0 desktop agentapi to check connection, create a user-requested conversation, send a scoped task, or read conversation metadata. Not a model proxy, quota tool, or GUI automation skill.
---

# Antigravity 2.0 Bridge

Announce use of this skill. The separate connector is `../../connector/antigravity_bridge.py` relative to the REAL location of this SKILL.md (resolve symlinks first). A user-level install is a symlink to this skill folder; do not copy this folder alone.

Use Python 3.9+. If macOS `/usr/bin/python3` only reports missing Xcode tools, use the installed Codex workspace-dependencies Python returned by its runtime discovery tool; do not install Xcode or change global PATH for this task. Run `python3 <connector> --help` for argument placement and `doctor` for local discovery. If the sandbox blocks process inspection or connection, obtain the normal tool permission; never work around a denial using another interface.

## Workflow

1. Confirm the requested action and scope. A request to inspect does not authorize creating a conversation or sending work. Delegation must carry the user's file boundaries, preservation requirements and approval constraints; it cannot bypass the caller's restrictions.
2. `doctor` reads only desktop CLI help and local process/listener information. It does not contact an existing conversation. Multiple Antigravity servers require an explicit `--pid`; never choose the first one silently.
3. `metadata <conversation-id>` reads metadata, not full messages or proof that a file was changed. Never use unrelated conversations as connection probes. `--address` and the `ANTIGRAVITY_CSRF_TOKEN` environment variable can supply a connection without process discovery. Only loopback addresses are allowed.
4. `new --project-id <actual-project-id> --prompt-file <file>` prepares a new task; append `--execute` only when the user requested dispatch. Obtain the real project ID from the user or an authorized project reference. It is NOT a conversation ID, directory name, or invented UUID. The connector passes it as `ANTIGRAVITY_PROJECT_ID`; compatibility with the installed build still requires a live authorized test. If `project_id is required` persists, stop and report it; do not edit app databases or guess private RPC schemas.
5. `send <conversation-id> --prompt-file <file> --execute` sends once to an explicitly selected conversation. A prompt file is local private task content, not a public repository asset. The native CLI receives the prompt as an argument, so other same-user processes may see it. Do not include credentials.
6. A timeout/invalid response after a mutation means UNKNOWN delivery. Do not automatically retry: inspect the app or ask the user to avoid duplicate work. A returned ID proves creation only, not completion. Verify deliverables separately before claiming success.

## Examples

```bash
python3 <connector> doctor
python3 <connector> --pid <selected-pid> metadata <conversation-id>
python3 <connector> --pid <selected-pid> new --project-id <actual-project-id> --prompt-file /private/tmp/task.txt
python3 <connector> --pid <selected-pid> new --project-id <actual-project-id> --prompt-file /private/tmp/task.txt --execute
python3 <connector> --pid <selected-pid> send <conversation-id> --prompt-file /private/tmp/task.txt --execute
```

The default new/send behavior is a local dry run with no connection. Model is inherited from Antigravity unless explicitly requested; the observed desktop CLI accepts only `flash_lite`, `flash`, `pro`. Do not translate these into a claimed exact model. Do not force a Codex model name into this interface.

The connector never saves authentication tokens, automatically retries sends, changes sandbox settings, or installs background services. It does not promise that headless conversations appear in the desktop UI. See the repository README for verification status and GitHub packaging.
