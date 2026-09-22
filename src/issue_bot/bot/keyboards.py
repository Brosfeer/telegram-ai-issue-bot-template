from typing import Optional, List, Dict, Any, Tuple
from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from issue_bot.config import settings
from issue_bot.core.database import Database

AI_PROGRESS_STEPS = [
    "🔍 `[1/3] Auditing QA Observations & Media Attachments...`",
    "🧠 `[2/3] Inspecting Codebase Architecture & Diagnosing...`",
    "🚀 `[3/3] Authoring GitHub Issue Specifications...`"
]

def get_persistent_keyboard(user_id: Optional[int] = None) -> ReplyKeyboardMarkup:
    """Return docked persistent keyboard tailored to user role."""
    is_admin = False
    if user_id is not None and user_id > 0:
        is_admin = ((settings.ADMIN_USER_ID > 0 and user_id == settings.ADMIN_USER_ID) or Database.is_admin(user_id))

    if is_admin:
        keyboard = [
            [KeyboardButton("🤖 Trigger AI Issue"), KeyboardButton("📦 Current Batch")],
            [KeyboardButton("⚡ Quick Issue"), KeyboardButton("📋 Recent Issues")],
            [KeyboardButton("📊 Repo Status"), KeyboardButton("❓ Help")]
        ]
    else:
        keyboard = [
            [KeyboardButton("🤖 Trigger AI Issue")],
            [KeyboardButton("📦 Current Batch"), KeyboardButton("❓ Help")]
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

def format_batch_card(batch: Dict[str, Any], items: List[Dict[str, Any]], user_id: Optional[int] = None) -> Tuple[str, InlineKeyboardMarkup]:
    """Generate Markdown text and inline action buttons for an active staging batch."""
    is_admin = False
    if user_id is not None and user_id > 0:
        is_admin = ((settings.ADMIN_USER_ID > 0 and user_id == settings.ADMIN_USER_ID) or Database.is_admin(user_id))

    batch_id = batch["id"]
    status = batch.get("status", "open")
    count = len(items)
    img_count = sum(1 for it in items if it.get("item_type") == "image")
    text_count = sum(1 for it in items if it.get("item_type") == "text")

    status_badge = "🟡 `PROCESSING`" if status == "processing" else "🟢 `OPEN`"

    lines = [
        f"📦 *QA Staging Batch #{batch_id}*",
        "━━━━━━━━━━━━━━━━━━━",
        f"📊 *Status*: {status_badge}",
        f"📁 *Items*: `{count}` ({img_count} 🖼️ Screenshots, {text_count} 📝 Notes)",
        ""
    ]

    if not items:
        lines.append("ℹ️ *Batch is currently empty.*")
        lines.append("👇 Send screenshots or text notes to begin.\n")
    else:
        lines.append("*Registered Items:*")
        for idx, it in enumerate(items[-4:], start=max(1, count - 3)):
            itype = "🖼️" if it.get("item_type") == "image" else "📝"
            cap = (it.get("caption") or "Snapshot attached").strip()
            if len(cap) > 42:
                cap = cap[:39] + "..."
            lines.append(f"• {itype} `Item #{idx}`: {cap}")
        lines.append("")

    buttons = []
    if status != "processing" and items:
        if is_admin:
            buttons.append([
                InlineKeyboardButton("🤖 Trigger AI Issue", callback_data=f"batch:ai:{batch_id}"),
                InlineKeyboardButton("⚡ Quick Issue", callback_data=f"batch:quick:{batch_id}")
            ])
        else:
            buttons.append([
                InlineKeyboardButton("🤖 Trigger AI Issue", callback_data=f"batch:ai:{batch_id}")
            ])
        buttons.append([
            InlineKeyboardButton("🗑️ Clear Batch", callback_data=f"batch:clear:{batch_id}")
        ])

    return "\n".join(lines), InlineKeyboardMarkup(buttons)
