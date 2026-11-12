# Environment Configuration Specification (`.env`)

Every environment variable supported by `s-bros-bot` is documented below with its type, default fallback, and purpose.

| Variable | Type | Default | Required? | Description |
| :--- | :--- | :--- | :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | `string` | `""` | **Yes** | Telegram Bot API token obtained from `@BotFather`. |
| `ADMIN_USER_ID` | `integer` | `0` | **Yes** | Numeric Telegram User ID of the primary owner / super administrator (from `@userinfobot`). |
| `ALLOWED_USER_IDS` | `string` | `""` | No | Comma-separated list of initial numeric user IDs allowed to interact with the bot. |
| `TARGET_REPO_NAME` | `string` | `"owner/repo"` | **Yes** | GitHub repository identifier in `owner/repo` format where issues and sub-issues will be created. |
| `TARGET_REPO_DIR` | `path` | Current Dir | **Yes** | Absolute directory path of the codebase repository on the server / local machine. |
| `TARGET_BASE_BRANCH` | `string` | `"main"` | No | Target base branch for code inspection and issue context. |
| `STORAGE_DIR` | `path` | `"data/images"`| No | Local directory where incoming screenshots are persisted before GitHub upload. |
| `DB_PATH` | `path` | `"data/bot.db"` | No | File path for SQLite database running in Write-Ahead Logging (`WAL`) mode. |
| `AGY_PATH` | `path` | `"agy"` | No | Absolute or system PATH to Antigravity / AGY CLI binary for deep AI inspection. |
| `LOG_LEVEL` | `string` | `"INFO"` | No | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
