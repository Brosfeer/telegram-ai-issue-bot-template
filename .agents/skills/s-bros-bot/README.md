# 🤖 `s-bros-bot` — Autonomous Telegram AI Issue Bot Skill

> **Universal Antigravity & AI Coding Agent Skill for automated setup, repository binding, pre-flight verification, and 24/7 daemon deployment of Telegram QA Issue Bots.**

[![Skill Standard](https://img.shields.io/badge/Antigravity%20Skill-v2.0-blue.svg)](https://github.com/Brosfeer/telegram-ai-issue-bot-template)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)

---

## 🌟 What is `s-bros-bot`?

`s-bros-bot` is a portable operational skill that enables AI coding assistants (Antigravity, Saya, Claude Code, Cursor) and human developers to connect any software codebase to an automated Telegram QA Issue Bot.

When mobile QA testers capture app screenshots and send them to Telegram, the bot debounces photo albums, uploads assets directly to GitHub's secure CDN via `gh --attach`, generates clean native Sub-Issues (`--parent`), and uses deep LLM inspection to cluster issues by UI screen and component files.

---

## ⚡ How to Call & Use It

### Method 1: Natural Language (Autonomous Progressive Disclosure)
Simply tell your AI assistant inside your project:
> *"Set up an s-bros-bot Telegram issue bot for this repository."*  
> *"Configure the issue bot credentials and run pre-flight checks."*  
> *"Authorize tester ID 123456789 in the bot database."*

The agent reads the skill's description, activates the procedural runbook in `SKILL.md`, and executes the setup.

### Method 2: Explicit Invocation
```text
/skill s-bros-bot
```
Or run the automation scripts directly from your terminal.

---

## 📁 Skill Package Contents

```text
s-bros-bot/
├── SKILL.md                          # Main procedural runbook & YAML frontmatter
├── README.md                         # Standalone documentation & guide
│
├── scripts/                          # Zero-dependency Python automation CLI tools
│   ├── detect_repo.py                # Extracts GitHub owner/repo, branch, and directory
│   ├── setup_bot.py                  # Generates or merges .env with detected repo settings
│   ├── verify_preflight.py           # Zero-guess pre-flight health auditor
│   └── manage_users.py               # User whitelist & authorization CLI
│
└── references/                       # In-depth architectural & operational specs
    ├── architecture.md               # Clean DAG architecture & sequence flows
    ├── env_spec.md                   # Complete environment variable schema
    └── troubleshooting.md            # Recovery steps for locks, tokens & ports
```

---

## 🚀 5-Minute Setup Runbook

### Step 1: Detect Repository Ground Truth
```bash
python3 .agents/skills/s-bros-bot/scripts/detect_repo.py
```
Automatically extracts your GitHub remote URL, target directory, and active branch without guessing.

### Step 2: Configure Credentials (`.env`)
```bash
python3 .agents/skills/s-bros-bot/scripts/setup_bot.py \
  --token "<YOUR_TELEGRAM_BOT_TOKEN>" \
  --admin "<YOUR_NUMERIC_TELEGRAM_USER_ID>"
```

### Step 3: Run Pre-Flight Sanity Checks
```bash
python3 .agents/skills/s-bros-bot/scripts/verify_preflight.py
```
Audits:
- Python 3.10+ runtime.
- Telegram Bot API token via `getMe`.
- GitHub CLI authentication and repository write access.
- SQLite WAL mode and permissions.

### Step 4: Manage Authorized Testers
```bash
# List authorized users and pending requests:
python3 .agents/skills/s-bros-bot/scripts/manage_users.py --list

# Authorize a tester:
python3 .agents/skills/s-bros-bot/scripts/manage_users.py --add 123456789 --name "Alex" --role qa
```

### Step 5: Production Daemon Deployment (PM2)
```bash
pm2 start main.py --name "s-bros-bot" --interpreter .venv/bin/python
pm2 save
pm2 logs s-bros-bot --lines 50
```

---

## 📦 How to Install This Skill in Any Project

### Option A: Inside Your Project (Workspace Scope)
```bash
mkdir -p .agents/skills
cp -r /path/to/s-bros-bot .agents/skills/s-bros-bot
```

### Option B: Machine-Wide (Global Scope)
```bash
mkdir -p ~/.gemini/antigravity-cli/skills
cp -r /path/to/s-bros-bot ~/.gemini/antigravity-cli/skills/s-bros-bot
```

---

## 🇸🇦 نظرة عامة باللغة العربية

مهارة **`s-bros-bot`** هي مهارة تشغيلية ذكية ومستقلة لمساعدي البرمجة الذكية (Antigravity و Saya)، تتيح ربط أي مشروع برمجي ببوت تيليجرام متخصص في استقبال لقطات شاشة الجودة (QA) وإنشاء تذاكر GitHub Issues وتذاكر فرعية (Native Sub-Issues) بشكل آلي ودقيق.

### الأدوات المرفقة:
1. `detect_repo.py`: استخراج بيانات المستودع والفرع تلقائياً من Git.
2. `setup_bot.py`: إنشاء وضبط ملف `.env` وتهيئة مجلدات التخزين.
3. `verify_preflight.py`: فحص أمان استباقي شامل قبل تشغيل البوت.
4. `manage_users.py`: إدارة صلاحيات فريق المختبرين والمشرفين في SQLite.

---

## 📄 License

Distributed under the **MIT License**. Part of the **Saya & Brosfeer** Developer Ecosystem.
