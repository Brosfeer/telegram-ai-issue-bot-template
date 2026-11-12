#!/usr/bin/env python3
"""
detect_repo.py — Automatic Git Repository Ground Truth Inspector
Extracts target repo name, active branch, and absolute directory without guessing.
"""
import sys
import json
import re
import subprocess
from pathlib import Path

def run_git_command(args: list[str], cwd: Path) -> str:
    try:
        res = subprocess.run(
            ["git"] + args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=True
        )
        return res.stdout.strip()
    except Exception:
        return ""

def parse_github_remote(remote_url: str) -> str:
    """Extract owner/repo from SSH or HTTPS git URLs."""
    if not remote_url:
        return ""
    # SSH format: git@github.com:owner/repo.git
    m = re.search(r"git@[^:]+:([^/]+/[^/]+?)(?:\.git)?$", remote_url)
    if m:
        return m.group(1)
    # HTTPS format: https://github.com/owner/repo.git
    m = re.search(r"https?://[^/]+/([^/]+/[^/]+?)(?:\.git)?$", remote_url)
    if m:
        return m.group(1)
    return ""

def detect_repository_info(target_dir: Path | None = None) -> dict:
    cwd = target_dir.resolve() if target_dir else Path.cwd().resolve()
    repo_root = run_git_command(["rev-parse", "--show-toplevel"], cwd)
    actual_dir = Path(repo_root) if repo_root else cwd

    remote_url = run_git_command(["remote", "get-url", "origin"], actual_dir)
    repo_name = parse_github_remote(remote_url)
    branch = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"], actual_dir) or "main"

    return {
        "target_repo_dir": str(actual_dir),
        "target_repo_name": repo_name or "owner/repository",
        "target_base_branch": branch,
        "remote_url": remote_url,
        "is_git_repo": bool(repo_root)
    }

def main():
    json_mode = "--json" in sys.argv
    info = detect_repository_info()

    if json_mode:
        print(json.dumps(info, indent=2))
        return

    print("🔍 [s-bros-bot] Detected Repository Ground Truth:")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"📁 Target Directory   : {info['target_repo_dir']}")
    print(f"🐙 GitHub Target Repo : {info['target_repo_name']}")
    print(f"🌿 Active Base Branch : {info['target_base_branch']}")
    print(f"🔗 Remote URL         : {info['remote_url'] or '(none)'}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

if __name__ == "__main__":
    main()
