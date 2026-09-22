import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from issue_bot.config import settings
from issue_bot.core.database import Database
from issue_bot.services.gatekeeper import validate_batch_relevance
from issue_bot.services.quick_issue_service import create_quick_issue_from_batch
from issue_bot.services.github_service import (
    extract_issue_url_and_number,
    find_related_open_ui_issue,
    attach_images_to_issue
)
from issue_bot.services.sub_issue_service import append_sub_issues_to_github_issue

logger = logging.getLogger(__name__)

async def create_ai_issue_from_batch(
    batch_id: int,
    custom_instruction: Optional[str] = None
) -> Dict[str, Any]:
    """Autonomous AI analysis and GitHub issue authoring via AI Agent CLI."""
    items = Database.get_batch_items(batch_id)
    if not items:
        return {"success": False, "error": "Batch is empty"}

    is_rel, reason = validate_batch_relevance(items, custom_instruction)
    if not is_rel:
        return {"success": False, "error": f"Batch rejected by Gatekeeper: {reason}"}

    first_item = items[0]
    user_id = first_item.get("user_id")

    # Smart Routing check
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

    # If AGY CLI is available, call it; otherwise fallback gracefully to quick_issue_service
    if not settings.AGY_PATH.exists():
        logger.info("AI CLI not found on host; falling back to standard Quick Issue.")
        return await create_quick_issue_from_batch(batch_id, custom_instruction=custom_instruction)

    # Compile prompt
    prompt = (
        f"Analyze QA Batch #{batch_id} for repository {settings.TARGET_REPO_NAME}. "
        f"Inspect codebase and create an architectural GitHub Issue with root cause analysis. "
        f"Instruction: {custom_instruction or 'Audit and document reported defects.'}"
    )

    cmd = [
        str(settings.AGY_PATH),
        "--cwd", str(settings.TARGET_REPO_DIR),
        "-p", prompt
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode().strip()
        parsed = extract_issue_url_and_number(output)
        if parsed:
            Database.record_issue(
                batch_id=batch_id,
                user_id=user_id,
                issue_number=parsed["issue_number"],
                issue_url=parsed["issue_url"],
                title=f"AI QA Synthesis (Batch #{batch_id})",
                created_by_ai=True
            )
            Database.close_batch(batch_id)
            return {
                "success": True,
                "issue_number": parsed["issue_number"],
                "issue_url": parsed["issue_url"],
                "created_by_ai": True,
                "items_count": len(items)
            }
    except Exception as e:
        logger.warning(f"AI CLI execution failed ({e}); falling back to Quick Issue.")

    return await create_quick_issue_from_batch(batch_id, custom_instruction=custom_instruction)
