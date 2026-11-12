#!/usr/bin/env python3
"""
manage_users.py — Standalone User Permission & Whitelist CLI for s-bros-bot
Inspect, authorize, promote, and revoke QA testers and Administrators in SQLite.
"""
import sys
import argparse
import sqlite3
from pathlib import Path

def get_db_path() -> Path:
    project_root = Path.cwd().resolve()
    env_file = project_root / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("DB_PATH="):
                    p = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                    target = Path(p)
                    return target if target.is_absolute() else project_root / target
    return project_root / "data" / "bot.db"

def list_users(db_path: Path):
    if not db_path.exists():
        print(f"❌ Database file not found at {db_path}. Has the bot been initialized?")
        return
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("\n👥 Authorized Team Members:")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"{'User ID':<14} | {'Role':<8} | {'Username':<18} | {'First Name':<16}")
    print("─" * 66)

    cursor.execute("SELECT user_id, role, username, first_name FROM authorized_users ORDER BY role ASC, id ASC")
    rows = cursor.fetchall()
    if not rows:
        print("(No authorized users registered yet)")
    for r in rows:
        uname = f"@{r['username']}" if r['username'] else "(none)"
        fname = r['first_name'] or "Tester"
        print(f"{r['user_id']:<14} | {r['role'].upper():<8} | {uname:<18} | {fname:<16}")

    print("\n⏳ Pending Access Requests:")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    cursor.execute("SELECT user_id, username, first_name, last_requested_at FROM access_requests WHERE status = 'pending'")
    reqs = cursor.fetchall()
    if not reqs:
        print("(No pending access requests)")
    for req in reqs:
        uname = f"@{req['username']}" if req['username'] else "(none)"
        print(f"ID: {req['user_id']} | User: {req['first_name']} ({uname}) | Requested: {req['last_requested_at']}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    conn.close()

def add_user(db_path: Path, user_id: int, name: str, role: str, username: str = None):
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO authorized_users (user_id, username, first_name, role, authorized_by)
        VALUES (?, ?, ?, ?, 0)
        ON CONFLICT(user_id) DO UPDATE SET
            role = excluded.role,
            first_name = excluded.first_name,
            username = excluded.username
    """, (user_id, username, name, role.lower()))
    cursor.execute("DELETE FROM access_requests WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    print(f"✅ User {user_id} ('{name}') authorized successfully with role '{role.upper()}'.")

def revoke_user(db_path: Path, user_id: int):
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("DELETE FROM authorized_users WHERE user_id = ?", (user_id,))
    deleted = cursor.rowcount > 0
    cursor.execute("UPDATE access_requests SET status = 'rejected' WHERE user_id = ?", (user_id,))
    cursor.execute("UPDATE batches SET status = 'cancelled' WHERE user_id = ? AND status = 'open'", (user_id,))
    conn.commit()
    conn.close()
    if deleted:
        print(f"🚫 User {user_id} access revoked.")
    else:
        print(f"⚠️ User {user_id} was not found in authorized users table.")

def main():
    parser = argparse.ArgumentParser(description="Manage authorized users for s-bros-bot")
    parser.add_argument("--list", action="store_true", help="List all authorized users and pending requests")
    parser.add_argument("--add", type=int, help="Telegram User ID to authorize")
    parser.add_argument("--name", default="Team Member", help="Name of the user")
    parser.add_argument("--username", help="Telegram @username")
    parser.add_argument("--role", default="qa", choices=["qa", "admin"], help="Role (qa or admin)")
    parser.add_argument("--revoke", type=int, help="Telegram User ID to revoke")
    args = parser.parse_args()

    db_path = get_db_path()

    if args.list or len(sys.argv) == 1:
        list_users(db_path)
    elif args.add:
        add_user(db_path, args.add, args.name, args.role, args.username)
    elif args.revoke:
        revoke_user(db_path, args.revoke)

if __name__ == "__main__":
    main()
