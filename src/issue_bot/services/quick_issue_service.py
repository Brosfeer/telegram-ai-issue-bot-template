import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from issue_bot.config import settings
from issue_bot.core.database import Database
from issue_bot.services.gatekeeper import validate_batch_relevance
from issue_bot.services.github_service import (
    extract_issue_url_and_number,
    detect_primary_label,
    format_title_case,
    find_related_open_ui_issue
)
from issue_bot.services.sub_issue_service import append_sub_issues_to_github_issue

logger = logging.getLogger(__name__)

async def create_quick_issue_from_batch(
    batch_id: int,
    custom_title: Optional[str] = None,
    custom_instruction: Optional[str] = None
) -> Dict[str, Any]:
    """Compile items in staging batch into an actionable GitHub Issue."""
    items = Database.get_batch_items(batch_id)
    if not items:
        return {"success": False, "error": "Batch is empty"}

    is_rel, reason = validate_batch_relevance(items, custom_instruction)
    if not is_rel:
        return {"success": False, "error": f"Batch rejected by Gatekeeper: {reason}"}

    first_item = items[0]
    user_id = first_item.get("user_id")

    # Smart Routing: Check for open UI parent issue
    candidate_caption = custom_instruction or first_item.get("caption") or ""
    parent_issue = await find_related_open_ui_issue(candidate_caption)
    if parent_issue:
        res = await append_sub_issues_to_github_issue(
            parent_issue_number=parent_issue["number"],
            batch_id=batch_id,
            custom_instruction=custom_instruction
        )
        res["appended_to_existing"] = True
        return res

    # Generate standalone issue
    title_seed = custom_title or first_item.get("caption") or f"Quality Assurance Review (Batch #{batch_id})"
    title = format_title_case(title_seed)
    primary_label = detect_primary_label(title_seed)

    body_lines = [
        "### 📌 Context & Problem Statement",
        f"Consolidated QA observation batch `#{batch_id}` submitted for `{settings.TARGET_REPO_NAME}`.",
        "",
        "### 📝 Items & Detailed Observations",
    ]

    for idx, it in enumerate(items, start=1):
        cap = (it.get("caption") or f"Visual snapshot #{idx}").strip()
        body_lines.append(f"- **Item #{idx}**: {cap}")

    body_lines.extend([
        "",
        "### ✅ Verification Checklist",
        "- [ ] Identify root cause and component target.",
        "- [ ] Implement resolution adhering to Clean Architecture standards.",
        "- [ ] Verify with 100% passing test suites."
    ])

    body = "\n".join(body_lines)
    cmd = [
        "gh", "issue", "create",
        "--repo", settings.TARGET_REPO_NAME,
        "--title", title,
        "--body", body,
        "--label", primary_label
    ]

    image_paths = []
    for it in items:
        loc = it.get("local_path")
        if loc and Path(loc).exists() and Path(loc).stat().st_size > 0:
            cmd.extend(["--attach", str(Path(loc).resolve())])
            image_paths.append(Path(loc))

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(settings.TARGET_REPO_DIR)
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        err_msg = stderr.decode().strip()
        logger.error(f"Failed to create quick issue: {err_msg}")
        return {"success": False, "error": err_msg}

    output = stdout.decode().strip()
    parsed = extract_issue_url_and_number(output)
    if not parsed:
        return {"success": False, "error": f"Could not parse issue URL from: {output}"}

    Database.record_issue(
        batch_id=batch_id,
        user_id=user_id,
        issue_number=parsed["issue_number"],
        issue_url=parsed["issue_url"],
        title=title,
        labels=primary_label,
        created_by_ai=False
    )
    Database.close_batch(batch_id)

    return {
        "success": True,
        "issue_number": parsed["issue_number"],
        "issue_url": parsed["issue_url"],
        "title": title,
        "items_count": len(items),
        "created_by_ai": False
    }
