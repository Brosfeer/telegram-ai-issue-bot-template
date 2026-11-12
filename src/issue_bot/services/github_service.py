import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from issue_bot.config import settings

logger = logging.getLogger(__name__)

def extract_issue_url_and_number(text: str) -> Optional[Dict[str, Any]]:
    """Extract GitHub issue URL and issue number from gh CLI output."""
    match = re.search(r"(https://github\.com/[^/\s]+/[^/\s]+/issues/(\d+))", text)
    if match:
        return {
            "issue_url": match.group(1).strip(),
            "issue_number": int(match.group(2))
        }
    return None

def detect_primary_label(text: str) -> str:
    """Detect whether issue is primarily a bug or an enhancement."""
    lowered = (text or "").lower()
    bug_keywords = ["bug", "crash", "error", "broken", "fix", "issue", "fails", "fail", "freeze", "null", "undefined"]
    if any(k in lowered for k in bug_keywords):
        return "bug"
    return "enhancement"

def format_title_case(raw_title: str) -> str:
    """Convert raw issue title to Title Case convention."""
    clean = re.sub(r'[\r\n]+', ' ', (raw_title or "").strip())
    if not clean:
        clean = "Quality Assurance Observation"

    prefix_match = re.match(r"^((?:Feat|Bug|Fix|Refactor|Chore|Docs)\([^)]+\)):\s*(.+)$", clean, re.IGNORECASE)
    if prefix_match:
        prefix = prefix_match.group(1).title()
        rest = prefix_match.group(2)
        words = rest.split()
        capitalized = " ".join([w.capitalize() if not w.startswith("#") else w for w in words])
        return f"{prefix}: {capitalized}"

    words = clean.split()
    capitalized = " ".join([w.capitalize() if not w.startswith("#") else w for w in words])
    label = detect_primary_label(clean)
    scope = "Bug(ui)" if label == "bug" else "Feat(ui)"
    return f"{scope}: {capitalized}"

def is_ui_context(text: str) -> bool:
    """Classify if the feedback text relates to UI styling/visual alignment."""
    lowered = (text or "").lower()
    ui_indicators = [
        "ui", "ux", "design", "layout", "padding", "margin", "radius", "border",
        "color", "font", "typography", "icon", "navbar", "header", "tabs", "card",
        "shadow", "blur", "dark mode", "light mode", "rtl", "align", "gap", "spacing"
    ]
    return any(k in lowered for k in ui_indicators)

async def attach_images_to_issue(issue_number: int, image_paths: List[Path]) -> bool:
    """Upload and attach local images directly to a GitHub issue via gh CLI."""
    if not image_paths:
        return True

    valid_images = [p for p in image_paths if p.exists() and p.stat().st_size > 0]
    if not valid_images:
        return True

    cmd = ["gh", "issue", "comment", str(issue_number), "--repo", settings.TARGET_REPO_NAME, "--body", "### 📸 Attached QA Screenshots"]
    for img in valid_images:
        cmd.extend(["--attach", str(img.resolve())])

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(settings.TARGET_REPO_DIR)
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.error(f"Failed to attach images to issue #{issue_number}: {stderr.decode()}")
        return False
    return True

async def get_repo_recent_issues(limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch recent open issues from target GitHub repository."""
    cmd = [
        "gh", "issue", "list",
        "--repo", settings.TARGET_REPO_NAME,
        "--limit", str(limit),
        "--json", "number,title,url,createdAt,state,labels,assignees"
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(settings.TARGET_REPO_DIR)
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.error(f"Failed to fetch recent issues: {stderr.decode()}")
        return []
    try:
        return json.loads(stdout.decode().strip())
    except Exception:
        return []

async def get_full_issue_details(issue_number: int) -> Optional[Dict[str, Any]]:
    """Fetch complete issue details including body via gh CLI."""
    cmd = [
        "gh", "issue", "view", str(issue_number),
        "--repo", settings.TARGET_REPO_NAME,
        "--json", "number,title,body,url,state,labels"
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(settings.TARGET_REPO_DIR)
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        return None
    try:
        return json.loads(stdout.decode().strip())
    except Exception:
        return None

async def find_related_open_ui_issue(caption: str) -> Optional[Dict[str, Any]]:
    """Search for an existing open UI parent issue to append sub-tasks to."""
    if not is_ui_context(caption):
        return None

    recent_issues = await get_repo_recent_issues(limit=10)
    for iss in recent_issues:
        title = iss.get("title", "").lower()
        if "ui" in title or "design" in title or "layout" in title:
            return iss
    return None

async def get_repo_status_summary() -> Dict[str, Any]:
    """Retrieve repository summary status via gh CLI."""
    cmd = ["gh", "issue", "status", "--repo", settings.TARGET_REPO_NAME]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(settings.TARGET_REPO_DIR)
    )
    stdout, stderr = await proc.communicate()
    return {
        "repo": settings.TARGET_REPO_NAME,
        "base_branch": settings.TARGET_BASE_BRANCH,
        "output": stdout.decode().strip() or stderr.decode().strip() or "No active issues."
    }
