# Session Memory — Telegram AI Issue Bot Template

This file contains reusable operating guidance for this template. Keep machine-specific paths, credentials, personal user IDs, private project histories, and production incident details out of it.

## What the bot does

The bot collects QA screenshots and notes in Telegram, groups related uploads into batches, and publishes GitHub issues in the configured target repository. It supports quick issue creation and AI-assisted issue synthesis, creates native GitHub sub-issues for multi-item reports, and stores local batch state and uploaded images under the configured data paths.

## Setup and configuration

1. Install Python 3.10+, GitHub CLI (`gh`), and (for AI synthesis) the AGY CLI. Authenticate `gh` with permission to create issues in the target repository.
2. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and set the Telegram bot token, admin Telegram ID, target GitHub repository (`owner/repository`), target repository directory, and optional base branch and AGY executable path. Keep `.env` private; never commit real credentials or user IDs.
4. Run the setup skill's repository detector, environment setup, and pre-flight checks before starting the bot:
   ```bash
   python3 .agents/skills/s-bros-bot/scripts/detect_repo.py
   python3 .agents/skills/s-bros-bot/scripts/setup_bot.py --interactive
   python3 .agents/skills/s-bros-bot/scripts/verify_preflight.py
   ```
5. Start locally with `python main.py`. For a persistent PM2 process, follow the deployment commands in `.agents/skills/s-bros-bot/SKILL.md`.

## Using the bot

- Send a screenshot with an optional caption, or send multiple screenshots and notes to stage a batch. Reply to a photo or send a note after an uncaptioned photo to associate the note with that screenshot.
- Use the bot's Quick Issue action for a fast report, or Trigger AI for code-aware synthesis and screen/component grouping. Use the isolated screenshot action for one standalone report; item removal and date-scoped batch actions are available from the batch card when shown.
- Use `/batch` to review staged items, `/clear` to clear the active batch, `/menu` to restore the keyboard, and `/help` for the bot's current help text. Command availability may depend on user role.
- Admins can manage access requests and authorized QA users through the bot or the `manage_users.py` CLI documented in the skill.
- The bot is for actionable software QA reports. Do not use it for casual conversation or consumer shopping requests.

## `s-bros-bot` operations skill

The workspace skill at `.agents/skills/s-bros-bot/` is the reusable setup and operations runbook for deploying this bot against any Git repository. It covers repository detection, `.env` setup, pre-flight verification, tester access management, and PM2 deployment/recovery. Read its `SKILL.md` before setup or operations; use the references for architecture, environment variables, and troubleshooting. Never put actual tokens or private user data in skill examples or documentation.

## Development guidance

- Preserve the clean dependency direction: config/core -> services -> bot; services must not import from bot. Keep Telegram event handlers separated by event type under `src/issue_bot/bot/handlers/`.
- Route each bot's notifications and GitHub work only through its configured target project.
- Keep secrets in ignored local environment files, and keep uploaded screenshots, SQLite databases, logs, and runtime state out of Git.
- Run `pytest -v` when verification is requested or required by the task.
