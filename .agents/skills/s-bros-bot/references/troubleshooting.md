# Troubleshooting & Recovery Runbook

### 1. Conflict: Terminated by Other getUpdates (`HTTP 409`)
- **Cause**: Another bot process is running with the same Telegram Bot Token (e.g. older PM2 process or local shell).
- **Remedy**:
  ```bash
  # Check running python bot instances
  pgrep -fl main.py
  # Stop duplicate processes or restart via PM2
  pm2 restart s-bros-bot
  ```

### 2. GitHub CLI Not Authorized (`gh auth status` error)
- **Cause**: The GitHub CLI token is missing or has expired.
- **Remedy**:
  ```bash
  gh auth login
  # Ensure scopes include 'repo' and 'read:org'
  gh auth status
  ```

### 3. Stuck Batch Lock (`status = 'processing'`)
- **Cause**: A crash occurred during LLM synthesis while the batch was locked.
- **Remedy**:
  Run this quick Python command to release stuck processing locks:
  ```bash
  python3 -c "import sqlite3; conn = sqlite3.connect('data/bot.db'); conn.execute(\"UPDATE batches SET status='open' WHERE status='processing'\"); conn.commit(); print('Locks released.')"
  ```

### 4. Database Disk I/O Error / Permission Denied
- **Cause**: The `data/` directory or `data/bot.db` is owned by root or another user.
- **Remedy**:
  ```bash
  sudo chown -R $USER:$USER data/
  chmod 755 data/
  chmod 644 data/bot.db*
  ```
