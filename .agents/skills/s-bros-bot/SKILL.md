---
name: s-bros-bot
description: >-
  Automates the setup, repository binding, pre-flight verification, environment configuration,
  and PM2 daemon deployment of Telegram AI Issue Bots for any Git repository.
  Use when the user asks to setup, configure, link, verify, or deploy an issue bot for their project.
---

# `s-bros-bot` — Autonomous Telegram AI Issue Bot Operations & Setup Skill

The `s-bros-bot` skill empowers AI coding assistants and developers to spin up, configure, bind, and operate a production-grade Telegram QA Issue Bot dedicated to **any software repository**.

It automates target repository binding, environment variable provisioning, pre-flight sanity auditing, SQLite WAL permission initialization, and background process management.

---

## 🎯 When to Use This Skill

Activate this skill whenever:
- A user wants to set up a Telegram bot to collect QA screenshots and create GitHub issues for their repository.
- A user asks to configure credentials (`.env`, `TELEGRAM_BOT_TOKEN`, `ADMIN_USER_ID`, `TARGET_REPO_NAME`).
- A user or agent needs to run pre-flight sanity checks before launching the bot daemon.
- An administrator needs to list, authorize, or revoke QA testers in SQLite without hand-writing SQL.
- A running bot encounters polling locks, concurrency conflicts, or permission issues.

---

## 🛠️ Step-by-Step Procedure

### Step 1: Detect Repository Ground Truth
Before guessing repository names or paths, run the repository detector to extract the ground truth directly from Git:

```bash
python3 .agents/skills/s-bros-bot/scripts/detect_repo.py
```

This returns:
- **`TARGET_REPO_DIR`**: Absolute path of the current project directory.
- **`TARGET_REPO_NAME`**: Normalized GitHub `owner/repository` string parsed from `git remote get-url origin`.
- **`TARGET_BASE_BRANCH`**: Current active working branch (e.g. `main`, `master`, `dev`).

To output in raw JSON for automated scripting:
```bash
python3 .agents/skills/s-bros-bot/scripts/detect_repo.py --json
```

---

### Step 2: Configure Environment (`.env`)
Generate or update the project `.env` file using the configuration script:

```bash
# Automated configuration using detected repo details:
python3 .agents/skills/s-bros-bot/scripts/setup_bot.py \
  --token "<TELEGRAM_BOT_TOKEN>" \
  --admin "<ADMIN_TELEGRAM_USER_ID>"
```

Or run interactively:
```bash
python3 .agents/skills/s-bros-bot/scripts/setup_bot.py --interactive
```

The script automatically:
1. Detects and resolves the target repo and base branch.
2. Creates or merges `.env` without overwriting existing unrelated keys.
3. Creates required storage folders: `data/images/` and `data/`.

---

### Step 3: Run Zero-Guess Pre-Flight Verification
Always run pre-flight checks before launching or restarting the bot daemon:

```bash
python3 .agents/skills/s-bros-bot/scripts/verify_preflight.py
```

This audits:
- **Python Version**: Confirms Python 3.10+ runtime.
- **Telegram Bot API**: Pings Telegram's `getMe` endpoint to verify the bot token and displays `@bot_username`.
- **Admin Configuration**: Validates that `ADMIN_USER_ID` is a non-zero integer.
- **GitHub CLI (`gh`)**: Verifies `gh auth status` and checks write/issue permissions on `TARGET_REPO_NAME`.
- **SQLite WAL Storage**: Verifies read/write access to SQLite database in WAL mode (`PRAGMA journal_mode = WAL;`).
- **Disk Storage**: Verifies write permissions in `data/images/`.

All checks must show `[PASS]` before starting the daemon.

---

### Step 4: Manage Authorized QA Testers
Manage authorized users and permissions directly via the management CLI:

```bash
# List all authorized users and pending access requests:
python3 .agents/skills/s-bros-bot/scripts/manage_users.py --list

# Authorize a new QA tester:
python3 .agents/skills/s-bros-bot/scripts/manage_users.py --add 123456789 --name "Alex" --role qa

# Promote a user to Admin:
python3 .agents/skills/s-bros-bot/scripts/manage_users.py --add 123456789 --name "Alex" --role admin

# Revoke a user's access:
python3 .agents/skills/s-bros-bot/scripts/manage_users.py --revoke 123456789
```

---

### Step 5: Production Daemon Deployment (PM2)
To keep the bot running 24/7 in the background with auto-restart on crashes or server reboots:

```bash
# Start bot under PM2:
pm2 start main.py --name "s-bros-bot" --interpreter .venv/bin/python

# Save process list for system reboot:
pm2 save

# View live streaming logs:
pm2 logs s-bros-bot --lines 50

# Restart daemon after code or configuration updates:
pm2 restart s-bros-bot
```

---

## 📚 References & Guides

- [Clean Package Architecture Blueprint](./references/architecture.md)
- [Environment Configuration Specification (`.env`)](./references/env_spec.md)
- [Troubleshooting & Emergency Recovery Runbook](./references/troubleshooting.md)
