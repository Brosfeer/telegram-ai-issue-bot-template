# SAYA SESSION MEMORY — Telegram AI Issue Bot Template

## Project Overview
- **Repository**: `Brosfeer/telegram-ai-issue-bot-template`
- **Location**: `/home/sharaf/projects/telegram-ai-issue-bot-template`
- **Tech Stack**: Python 3.12+, `python-telegram-bot` (v20+ async), `sqlite3` WAL, `gh` GitHub CLI, `AGY` CLI, `pytest`.
- **Purpose**: Clean Architecture production-grade template for building dedicated GitHub QA Issue bots and Multi-Project Archival bots.

---

## Session Log: September 30, 2026 — Project Resync Architecture & Ecosystem Archaeology

### 1. Context & User Inquiry
- **Inquiry**: User inquired why the `🔄 Resync Projects` / `🔄 Refresh Projects` button was absent from bot keyboards and menus, how it originally functioned, and requested its analysis and reactivation.
- **Lineage Analysis**:
  - Investigated four interconnected repositories in the ecosystem:
    1. `telegram-ai-bot`: Original Node.js codex executor with simple `/projects` registry.
    2. `teleg_img_archive` (`@arc_me_bot`): Ideas and UI image archive bot where multi-project scanning was first implemented in `indexer.py`.
    3. `rakhys_issue_bot` (`@rakhys_issues_bot`): Dedicated single-repo QA Issue bot with batch staging and Saya AI synthesis.
    4. `telegram-ai-issue-bot-template`: Clean architecture open-source template distilled from Rakhys.

### 2. Forensic Findings & Root Cause Analysis
- **Original Implementation (`teleg_img_archive` Commit `94f2ba2`)**:
  - `indexer.py` scanned `/home/sharaf/projects`, registered project names in SQLite, and copied image assets from codebase trees.
- **De-scoping (`ad79fe7`)**:
  - Feature was temporarily removed to focus on Telegram-uploaded images (`projects/<project>/telegram_images/`).
- **Unmerged Pull Request #2 (`feat/issue-1-refresh-reindex-projects`)**:
  - Re-implemented clean, non-bloating project registration without copying code assets.
  - Pull Request #2 was closed without merging into `main`.
  - Later features (Saya AI integration, issue consolidation, auto-assign) branched directly off `main`, leaving the `🔄 Refresh Projects` button and `indexer.py` uncalled and orphaned.

### 3. Solution Implemented in Running Ecosystem (`teleg_img_archive`)
- **Background Indexer Engine**:
  - Updated `indexer.py` with `scan_and_index_projects()` scanning `SCAN_BASE_DIR` (`/home/sharaf/projects`).
  - Strict exclusion filtering for `system-monitor`, `.git`, `node_modules`, `.venv`, and build directories.
  - Zero-bloat guarantee: registers project metadata into SQLite without copying code assets.
- **Telegram Bot User Interface**:
  - Added `[ 🔄 Refresh Projects ]` to the persistent docked keyboard (`ReplyKeyboardMarkup(..., is_persistent=True)`).
  - Added `[ 🔄 Re-index / Refresh Projects ]` inline button (`menu_refresh_projects`) to the project selector.
  - Registered `/refresh`, `/scan`, and `/resync` commands running asynchronously via `asyncio.to_thread`.
- **Empirical Verification**:
  - 64/64 pytest unit tests passing (100%).
  - Live PM2 daemon `teleg_img_archive` restarted and validated online.

---

## Architectural Guidelines for Multi-Project Issue Bots
When extending this template for multi-project workflows:
1. **Never Crawl or Duplicate Codebase Image Assets**: Track only user-uploaded Telegram screenshots in `projects/<project>/telegram_images/`.
2. **Non-Blocking Threading**: Always run disk directory traversal inside `asyncio.to_thread` to prevent Telegram polling lag.
3. **Docked Keyboard Parity**: Ensure `is_persistent=True` is preserved on all ReplyKeyboardMarkup instances.
