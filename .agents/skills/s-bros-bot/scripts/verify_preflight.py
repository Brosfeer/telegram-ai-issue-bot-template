#!/usr/bin/env python3
"""
verify_preflight.py — Zero-Guess Pre-Flight Environment & Health Auditor for s-bros-bot
Validates Telegram token, GitHub CLI auth, target repository access, SQLite WAL, and permissions.
"""
import sys
import os
import json
import sqlite3
import subprocess
import urllib.request
from pathlib import Path

def print_result(check_name: str, passed: bool, message: str, warning: bool = False) -> None:
    badge = "✅ [PASS]" if passed else ("⚠️ [WARN]" if warning else "❌ [FAIL]")
    print(f"{badge:<10} {check_name:<28} : {message}")

def check_python_version() -> bool:
    v = sys.version_info
    ok = (v.major == 3 and v.minor >= 10)
    msg = f"Python {v.major}.{v.minor}.{v.micro}"
    print_result("Python Runtime", ok, msg)
    return ok

def load_env(env_path: Path) -> dict[str, str]:
    if not env_path.exists():
        return {}
    res = {}
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                res[k.strip()] = v.strip().strip('"').strip("'")
    return res

def check_telegram_token(token: str) -> bool:
    if not token or token.startswith("your_"):
        print_result("Telegram Bot Token", False, "Missing or set to placeholder in .env")
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        req = urllib.request.Request(url, headers={"User-Agent": "s-bros-bot-preflight/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok"):
                result = data.get("result", {})
                username = result.get("username", "unknown")
                name = result.get("first_name", "Bot")
                print_result("Telegram Bot API", True, f"Online as @{username} ('{name}')")
                return True
            else:
                print_result("Telegram Bot API", False, f"API returned error: {data}")
                return False
    except Exception as e:
        print_result("Telegram Bot API", False, f"Network or Token verification error: {e}")
        return False

def check_admin_user_id(admin_id_str: str) -> bool:
    try:
        admin_id = int(admin_id_str)
        if admin_id > 0:
            print_result("Admin User ID", True, f"Configured ID: {admin_id}")
            return True
        else:
            print_result("Admin User ID", False, "ADMIN_USER_ID must be a positive integer from @userinfobot")
            return False
    except Exception:
        print_result("Admin User ID", False, f"Invalid numeric format: '{admin_id_str}'")
        return False

def check_github_cli(repo_name: str) -> bool:
    try:
        res = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
        if res.returncode != 0:
            print_result("GitHub CLI Auth", False, "Not authenticated. Run 'gh auth login'")
            return False
        print_result("GitHub CLI Auth", True, "Authenticated with GitHub CLI")
    except FileNotFoundError:
        print_result("GitHub CLI", False, "'gh' executable not found on system PATH")
        return False

    if not repo_name or repo_name == "owner/repository":
        print_result("Target Repository Access", False, "TARGET_REPO_NAME is set to default placeholder", warning=True)
        return False

    try:
        res = subprocess.run(
            ["gh", "repo", "view", repo_name, "--json", "name,isPrivate,viewerPermission"],
            capture_output=True,
            text=True
        )
        if res.returncode == 0:
            data = json.loads(res.stdout)
            perm = data.get("viewerPermission", "unknown")
            print_result("Target Repository Access", True, f"'{repo_name}' accessible (Permission: {perm})")
            return True
        else:
            print_result("Target Repository Access", False, f"Cannot access '{repo_name}': {res.stderr.strip()}")
            return False
    except Exception as e:
        print_result("Target Repository Access", False, f"Error inspecting repository: {e}")
        return False

def check_sqlite_wal(db_path: Path) -> bool:
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode = WAL;")
        mode = cursor.fetchone()[0]
        cursor.execute("CREATE TABLE IF NOT EXISTS _preflight_check (id INTEGER PRIMARY KEY);")
        cursor.execute("INSERT INTO _preflight_check DEFAULT VALUES;")
        conn.commit()
        cursor.execute("DROP TABLE _preflight_check;")
        conn.commit()
        conn.close()
        print_result("SQLite WAL Storage", True, f"Write verified on {db_path.name} (mode={mode.upper()})")
        return True
    except Exception as e:
        print_result("SQLite WAL Storage", False, f"Database access failed: {e}")
        return False

def check_storage_dir(storage_path: Path) -> bool:
    try:
        storage_path.mkdir(parents=True, exist_ok=True)
        test_file = storage_path / ".preflight_write_test"
        test_file.write_text("ok")
        test_file.unlink()
        print_result("Media Storage Directory", True, f"Writable at {storage_path}")
        return True
    except Exception as e:
        print_result("Media Storage Directory", False, f"Storage directory unwritable: {e}")
        return False

def main():
    print("\n🔍 [s-bros-bot] Pre-Flight System & Configuration Audit:")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    project_root = Path.cwd().resolve()
    env_path = project_root / ".env"
    env = load_env(env_path)

    results = []
    results.append(check_python_version())

    if not env_path.exists():
        print_result(".env Configuration File", False, "Missing .env. Run 'python3 scripts/setup_bot.py'")
        sys.exit(1)
    else:
        print_result(".env Configuration File", True, f"Loaded from {env_path.name}")

    token = env.get("TELEGRAM_BOT_TOKEN", "")
    admin_id = env.get("ADMIN_USER_ID", "0")
    repo_name = env.get("TARGET_REPO_NAME", "")
    db_rel = env.get("DB_PATH", "data/bot.db")
    storage_rel = env.get("STORAGE_DIR", "data/images")

    results.append(check_telegram_token(token))
    results.append(check_admin_user_id(admin_id))
    results.append(check_github_cli(repo_name))
    results.append(check_sqlite_wal(project_root / db_rel))
    results.append(check_storage_dir(project_root / storage_rel))

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    all_passed = all(results)
    if all_passed:
        print("🎉 ALL CHECKS PASSED — Ready to run or deploy!")
        print("   To launch daemon: pm2 start main.py --name s-bros-bot --interpreter .venv/bin/python\n")
        sys.exit(0)
    else:
        print("⚠️ SOME CHECKS FAILED OR WARNED — Please address the issues listed above.\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
