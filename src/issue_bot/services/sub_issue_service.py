import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from issue_bot.config import settings
from issue_bot.core.database import Database
from issue_bot.services.github_service import (
    extract_issue_url_and_number,
    detect_primary_label,
    format_title_case
)

logger = logging.getLogger(__name__)

def diagnose_and_simplify_qa_item(caption: str) -> Dict[str, str]:
    """Analyze QA observation and synthesize engineering triage."""
    text = (caption or "").lower()
    subsystem = "Core UI & Styling"
    target_files = "src/, components/"
    diagnosis = "Visual layout, styling, or token divergence."
    simplification = f"Align layout: {caption.strip() if caption else 'Visual Inspection'}"

    if any(k in text for k in ["crash", "error", "exception", "freeze", "hang"]):
        subsystem = "Runtime & Exception Handling"
        target_files = "src/services/, src/handlers/"
        diagnosis = "Unhandled exception or state failure during operation."
        simplification = f"Resolve runtime defect: {caption.strip()}"
    elif any(k in text for k in ["api", "network", "timeout", "fetch"]):
        subsystem = "Networking & API Layer"
        target_files = "src/api/, src/services/"
        diagnosis = "Network timeout, serialization error, or unresponsive endpoint."
        simplification = f"Handle API response properly: {caption.strip()}"

    return {
        "subsystem": subsystem,
        "target_files": target_files,
        "diagnosis": diagnosis,
        "simplification": simplification
    }

async def append_sub_issues_to_github_issue(
    parent_issue_number: int,
    batch_id: int,
    custom_instruction: Optional[str] = None
) -> Dict[str, Any]:
    """Create native GitHub Sub-Issues under parent ticket via gh CLI."""
    items = Database.get_batch_items(batch_id)
    if not items:
        return {"success": False, "error": "Batch is empty"}

    parent_url = f"https://github.com/{settings.TARGET_REPO_NAME}/issues/{parent_issue_number}"
    sub_issues_created = []

    for idx, it in enumerate(items, start=1):
        cap = (it.get("caption") or f"Visual inspection snapshot #{idx}").strip()
        analysis = diagnose_and_simplify_qa_item(cap)
        sub_title = format_title_case(f"{analysis['simplification']} (Batch {batch_id}.{idx})")
        primary_label = detect_primary_label(cap)

        body_lines = [
            f"### 🎯 Architectural Decomposition (Batch {batch_id}.{idx})",
            "",
            f"| Attribute | Specification |",
            f"| :--- | :--- |",
            f"| 📌 **Parent Issue** | #{parent_issue_number} |",
            f"| 🏷️ **Subsystem** | `{analysis['subsystem']}` |",
            f"| 📁 **Target Scope** | `{analysis['target_files']}` |",
            f"| 🔍 **Root Cause** | {analysis['diagnosis']} |",
            "",
            "### 📝 QA Observation & Requirement",
            f"> {cap}",
            "",
            f"**Execution Directive**: {analysis['simplification']}.",
            "",
            "### ✅ Verification Gate",
            "- [ ] Unit tests pass with 100% success.",
            "- [ ] Visual alignment verified against design tokens."
        ]

        sub_body = "\n".join(body_lines)
        cmd = [
            "gh", "issue", "create",
            "--repo", settings.TARGET_REPO_NAME,
            "--title", sub_title,
            "--body", sub_body,
            "--label", primary_label,
            "--parent", str(parent_issue_number)
        ]

        loc = it.get("local_path")
        if loc and Path(loc).exists() and Path(loc).stat().st_size > 0:
            cmd.extend(["--attach", str(Path(loc).resolve())])

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(settings.TARGET_REPO_DIR)
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            parsed = extract_issue_url_and_number(stdout.decode())
            if parsed:
                sub_issues_created.append(parsed)

    Database.close_batch(batch_id)
    return {
        "success": True,
        "parent_issue_number": parent_issue_number,
        "parent_issue_url": parent_url,
        "sub_issues_created": sub_issues_created,
        "items_count": len(items)
    }
