# AGENTS — AI Agent Workflow & Clean Architecture Standard

This file defines mandatory architectural principles, directory layout constraints, and operational protocols for AI coding assistants (Google Antigravity, Cursor, Windsurf, Claude Code, GitHub Copilot) modifying or extending this Telegram Issue Bot template.

---

## 1. Architectural Philosophy: Clean Architecture & Strict DAG

This repository strictly enforces **Separation of Concerns (SoC)** and a **Directed Acyclic Graph (DAG)** dependency order:

```text
[ Config (settings.py) ]
       ▲             ▲
       │             │
  [ Core ]      [ Services ]
  - storage.py  - github_service.py
  - database.py - gatekeeper.py
                - sub_issue_service.py
                - quick_issue_service.py
                - ai_service.py
                     ▲
                     │
                 [ Bot ]
                 - keyboards.py
                 - helpers.py
                 - handlers/ (commands, media, text, callbacks)
                 - app.py
```

### Strict Architectural Guardrails:
1. **Never Violate Dependency Order**:
   - `core` depends only on `config`.
   - `services` depends on `config` and `core`. **Services must NEVER import from `bot`**.
   - `bot` depends on `services`, `core`, and `config`.
   - `main.py` is a thin launcher (~35 lines) that initializes settings and database, then calls `app.create_application().run_polling()`.
2. **No Monolithic File Anti-Pattern**:
   - Never pile commands, media listeners, and callback handlers into a single file.
   - All Telegram handlers must live in `src/issue_bot/bot/handlers/` separated by event type (`commands.py`, `media.py`, `text.py`, `callbacks.py`).
3. **Pure Platform Primitives & Zero Bloat (KISS & DRY)**:
   - Prefer Python standard library built-ins over unnecessary third-party dependencies.
   - For example: `inspect_image_file` in `storage.py` parses binary headers (`PNG`, `JPEG`, `WEBP`) using `struct` rather than pulling in heavy imaging packages.

---

## 2. Directory Layout & Subsystem Responsibilities

```text
src/
└── issue_bot/
    ├── config/             # Environment, path resolution, singleton settings
    │   ├── __init__.py
    │   └── settings.py     # Base directory, repository names, whitelist
    ├── core/               # Low-level infrastructure primitives
    │   ├── __init__.py
    │   ├── database.py     # SQLite WAL connection, migrations, batch locks
    │   └── storage.py      # Collision-resistant paths, binary header forensics
    ├── services/           # Domain business logic & external integrations
    │   ├── __init__.py
    │   ├── ai_service.py           # Autonomous LLM prompt authoring & triage
    │   ├── gatekeeper.py           # Domain keywords, chatter & batch relevance
    │   ├── github_service.py       # gh CLI wrapper, labeler & formatters
    │   ├── quick_issue_service.py  # 1-click issue publisher & matrix authoring
    │   └── sub_issue_service.py    # Native GitHub Sub-Issues (--parent)
    └── bot/                # Telegram presentation layer
        ├── __init__.py
        ├── app.py                  # Application builder & polling runner
        ├── helpers.py              # Auth middleware & scoped setMyCommands
        ├── keyboards.py            # Docked persistent keyboards & batch cards
        └── handlers/               # Modular event handlers
            ├── __init__.py
            ├── callbacks.py        # Inline button callbacks
            ├── commands.py         # Scoped command handlers (/start, /ai, /batch, etc.)
            ├── media.py            # Debounced photo and document album listeners
            └── text.py             # QA defect notes, button clicks & photo pairing
```

---

## 3. Mandatory Telegram Bot Design Rules

Whenever inspecting, adding, or modifying Telegram interactions:
1. **Docked Persistent Keyboards (`is_persistent=True`)**:
   - Every `ReplyKeyboardMarkup` must have `is_persistent=True` so the docked keyboard remains pinned when the user types on mobile or desktop clients.
2. **Native Scoped Command Menu (`set_my_commands`)**:
   - Register scoped commands via `application.post_init(set_bot_commands)`.
   - General testers receive streamlined commands (`/start`, `/ai`, `/batch`, `/clear`, `/menu`, `/help`).
   - Admins receive scoped administrative commands (`/users`, `/pending`, `/revoke`, `/quick`, `/status`, `/recent`).
3. **Instant Recall (`/menu`)**:
   - Always provide a dedicated `/menu` command so users can immediately restore the docked persistent keyboard.
4. **Media Group Album Debouncing**:
   - Multi-photo Telegram albums dispatch separate updates sharing a `media_group_id`.
   - Always debounce album ingestion with an async timer (`_send_debounced_batch_summary`) so the user receives a single consolidated batch card rather than multiple message spams.
5. **Smart Message Pairing**:
   - Support auto-adoption: subsequent text notes sent after an uncaptioned photo should pair automatically, or support photo reply targeting.
6. **Repository-Isolated Bot Alerting & Zero Cross-Bot Pollution**:
   - Notifications, alerts, reviews, and GitHub activity updates must strictly route through that specific repository's designated bot. Never alert project A events through project B's bot.

---

## 4. GitHub CLI & Issue Triage Rules

1. **Native Sub-Issues Hierarchy**:
   - Use `gh issue create --parent <parent_issue_number>` to decompose multi-item batches into native GitHub Sub-Issues rather than polluting parent issue bodies.
2. **Direct Asset Attachment**:
   - Use `gh issue create ... --attach <path>` and `gh issue comment ... --attach <path>` to upload screenshot files directly to GitHub's asset CDN.
3. **Format Titles with Title Case**:
   - All GitHub issues and PRs must use Title Case: `Bug(ui): Header Padding Misaligned` or `Feat(cart): Add Quick Checkout`.
4. **Batch Numbering Standard**:
   - Never use `#X.Y` in issue bodies or comments, as GitHub markdown autolinks `#X` to issue number `X`. Always use `Batch {batch_id}.{idx}` format.

---

## 5. Security & Access Control

1. **Multi-Tier Authorization**:
   - Admin Owner ID (`ADMIN_USER_ID`) retains permanent super-admin authority.
   - Dynamic Access Requests: Unauthorized users trigger an alert card sent to the Admin with `[ ✅ Approve ]` / `[ ❌ Reject ]` inline buttons.
   - Approved members are saved to SQLite `authorized_users`.
2. **Concurrency Batch Locking**:
   - Multi-click protection: batches transition from `open` to `processing` via `lock_batch_for_processing`. If processing, subsequent clicks are rejected until completed.

---

## 6. Verification & Testing Protocol

Before committing any change or completing any task:
1. **Run Pytest Test Suite**:
   ```bash
   pytest -v
   ```
   **Standard**: 100% tests passing with zero errors and zero warnings.
2. **Multi-Commit Granular Paper Trail**:
   - Never squash multi-layer changes into monolithic commits.
   - Commit logically: `Refactor(core): ...`, `Feat(services): ...`, `Feat(bot): ...`.
