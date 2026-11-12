#!/usr/bin/env python3
"""
setup_bot.py — Automated .env and Directory Provisioner for s-bros-bot
Configures environment variables, binds target repository, and prepares data folders.
"""
import sys
import argparse
from pathlib import Path
from detect_repo import detect_repository_info

def read_existing_env(env_path: Path) -> dict[str, str]:
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

def write_env_file(env_path: Path, values: dict[str, str]) -> None:
    lines = [
        "# ===================================================================",
        "# s-bros-bot Environment Configuration",
        "# Generated automatically by s-bros-bot skill",
        "# ===================================================================",
        "",
        "# Telegram Bot Credentials",
        f"TELEGRAM_BOT_TOKEN={values.get('TELEGRAM_BOT_TOKEN', '')}",
        f"ADMIN_USER_ID={values.get('ADMIN_USER_ID', '0')}",
        f"ALLOWED_USER_IDS={values.get('ALLOWED_USER_IDS', values.get('ADMIN_USER_ID', '0'))}",
        f"LOG_LEVEL={values.get('LOG_LEVEL', 'INFO')}",
        "",
        "# Target Repository Integration",
        f"TARGET_REPO_NAME={values.get('TARGET_REPO_NAME', 'owner/repository')}",
        f"TARGET_REPO_DIR={values.get('TARGET_REPO_DIR', '')}",
        f"TARGET_BASE_BRANCH={values.get('TARGET_BASE_BRANCH', 'main')}",
        "",
        "# Storage & Engine Paths",
        f"STORAGE_DIR={values.get('STORAGE_DIR', 'data/images')}",
        f"DB_PATH={values.get('DB_PATH', 'data/bot.db')}",
        f"AGY_PATH={values.get('AGY_PATH', 'agy')}",
        ""
    ]
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def main():
    parser = argparse.ArgumentParser(description="Configure environment for s-bros-bot")
    parser.add_argument("--token", help="Telegram Bot Token from @BotFather")
    parser.add_argument("--admin", help="Admin Telegram User ID (numeric, from @userinfobot)")
    parser.add_argument("--target-dir", help="Path to target codebase repository")
    parser.add_argument("--target-name", help="Target GitHub repository (owner/repo)")
    parser.add_argument("--branch", help="Target repository working branch")
    parser.add_argument("--interactive", action="store_true", help="Prompt for missing inputs interactively")
    parser.add_argument("--env-file", default=".env", help="Path to destination .env file")
    args = parser.parse_args()

    project_root = Path.cwd().resolve()
    env_path = project_root / args.env_file
    existing = read_existing_env(env_path)

    # Detect repo info from target dir or current dir
    detected = detect_repository_info(Path(args.target_dir) if args.target_dir else project_root)

    token = args.token or existing.get("TELEGRAM_BOT_TOKEN", "")
    admin_id = args.admin or existing.get("ADMIN_USER_ID", "0")
    target_name = args.target_name or existing.get("TARGET_REPO_NAME") or detected["target_repo_name"]
    target_dir = args.target_dir or existing.get("TARGET_REPO_DIR") or detected["target_repo_dir"]
    branch = args.branch or existing.get("TARGET_BASE_BRANCH") or detected["target_base_branch"]

    if args.interactive:
        print("\n⚙️ [s-bros-bot] Interactive Configuration Setup:")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        in_token = input(f"Telegram Bot Token [{token[:10]}...]: ").strip()
        if in_token:
            token = in_token
        in_admin = input(f"Admin Telegram User ID [{admin_id}]: ").strip()
        if in_admin:
            admin_id = in_admin
        in_tname = input(f"GitHub Repository (owner/repo) [{target_name}]: ").strip()
        if in_tname:
            target_name = in_tname
        in_tdir = input(f"Target Directory Path [{target_dir}]: ").strip()
        if in_tdir:
            target_dir = in_tdir
        in_branch = input(f"Target Branch [{branch}]: ").strip()
        if in_branch:
            branch = in_branch

    # Update dictionary
    existing["TELEGRAM_BOT_TOKEN"] = token
    existing["ADMIN_USER_ID"] = admin_id
    existing["ALLOWED_USER_IDS"] = existing.get("ALLOWED_USER_IDS", admin_id)
    existing["TARGET_REPO_NAME"] = target_name
    existing["TARGET_REPO_DIR"] = str(Path(target_dir).resolve())
    existing["TARGET_BASE_BRANCH"] = branch
    existing["STORAGE_DIR"] = existing.get("STORAGE_DIR", "data/images")
    existing["DB_PATH"] = existing.get("DB_PATH", "data/bot.db")
    existing["LOG_LEVEL"] = existing.get("LOG_LEVEL", "INFO")
    existing["AGY_PATH"] = existing.get("AGY_PATH", "agy")

    write_env_file(env_path, existing)

    # Create directories
    storage_dir = project_root / existing["STORAGE_DIR"]
    storage_dir.mkdir(parents=True, exist_ok=True)
    db_file = project_root / existing["DB_PATH"]
    db_file.parent.mkdir(parents=True, exist_ok=True)

    print("\n✅ [s-bros-bot] Configuration saved successfully to .env")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"🤖 Bot Token Configured : {'Yes (hidden)' if token else '❌ Missing (Set TELEGRAM_BOT_TOKEN)'}")
    print(f"👑 Admin User ID        : {admin_id}")
    print(f"🐙 Target GitHub Repo   : {target_name}")
    print(f"📁 Target Codebase Dir  : {target_dir}")
    print(f"🌿 Target Branch        : {branch}")
    print(f"💾 Storage Directory    : {storage_dir}")
    print(f"🗄️ Database Path        : {db_file}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("👉 Next step: Run pre-flight verification:")
    print("   python3 .agents/skills/s-bros-bot/scripts/verify_preflight.py\n")

if __name__ == "__main__":
    main()
