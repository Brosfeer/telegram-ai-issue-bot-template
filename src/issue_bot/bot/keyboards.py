from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
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

def format_batch_card(
    batch: Dict[str, Any],
    items: List[Dict[str, Any]],
    user_id: Optional[int] = None,
    new_item_id: Optional[int] = None
) -> Tuple[str, InlineKeyboardMarkup]:
    """Generate Markdown text and inline action buttons for an active staging batch."""
    is_admin = False
    if user_id is not None and user_id > 0:
        is_admin = ((settings.ADMIN_USER_ID > 0 and user_id == settings.ADMIN_USER_ID) or Database.is_admin(user_id))

    batch_id = batch["id"]
    status = batch.get("status", "open")
    count = len(items)
    img_count = sum(1 for it in items if it.get("item_type") == "image")
    text_count = sum(1 for it in items if it.get("item_type") == "text")

    # Date categorization: separate today's items from older sessions
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_items = [it for it in items if str(it.get("created_at", ""))[:10] == today_str]
    older_items = [it for it in items if str(it.get("created_at", ""))[:10] != today_str]

    status_badge = "🟡 `PROCESSING`" if status == "processing" else "🟢 `OPEN`"

    lines = [
        f"📦 *QA Staging Batch #{batch_id}*",
        "━━━━━━━━━━━━━━━━━━━",
        f"📊 *Status*: {status_badge}",
    ]

    if older_items and today_items:
        lines.append(f"📁 *Items*: `{count}` ({len(today_items)} Today ☀️, {len(older_items)} Earlier 🗓️)")
    else:
        lines.append(f"📁 *Items*: `{count}` ({img_count} 🖼️ Screenshots, {text_count} 📝 Notes)")
    lines.append("")

    if not items:
        lines.append("ℹ️ *Batch is currently empty.*")
        lines.append("👇 Send screenshots or text notes to begin.\n")
    else:
        lines.append("*Registered Items:*")
        recent_items = items[-4:]
        start_idx = max(1, count - len(recent_items) + 1)
        for offset, it in enumerate(recent_items):
            idx = start_idx + offset
            itype = "🖼️" if it.get("item_type") == "image" else "📝"
            cap = (it.get("caption") or "Snapshot attached").strip()
            is_today = str(it.get("created_at", ""))[:10] == today_str
            date_tag = " (Today)" if (older_items and is_today) else (" (Earlier)" if (older_items and not is_today) else "")
            if len(cap) > 36:
                cap = cap[:33] + "..."
            lines.append(f"`{idx}.` {itype} {cap}{date_tag}")
        lines.append("")

    if status == "processing":
        lines.append("⏳ *AI Issue Engine is actively analyzing this batch...*")
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh Status", callback_data=f"batch:refresh:{batch_id}")]
        ]
        return "\n".join(lines), InlineKeyboardMarkup(keyboard)

    keyboard = []

    # 1. Instant Single-Item Trigger
    if new_item_id:
        keyboard.append([
            InlineKeyboardButton("🚀 Issue This Screenshot Isolated", callback_data=f"single:ai:{new_item_id}")
        ])

    # 2. Date-Scoped Trigger: Offer "Today Only" when there's a mix of today and older items
    if today_items and older_items:
        keyboard.append([
            InlineKeyboardButton(f"☀️ Trigger Today Only ({len(today_items)} items)", callback_data=f"batch:today:{batch_id}")
        ])

    # 3. Main Batch Trigger
    if items:
        lines.append("👇 *Tap below when ready to generate the issue:*")
        btn_label = f"🤖 Trigger AI Issue ({count} items)" if count > 0 else "🤖 Trigger AI Issue"
        keyboard.append([
            InlineKeyboardButton(btn_label, callback_data=f"batch:ai:{batch_id}")
        ])

    # 4. Granular Item Drop Row (Drop individual items without clearing the whole batch)
    if items:
        drop_row = []
        recent_items = items[-4:]
        start_idx = max(1, count - len(recent_items) + 1)
        for offset, it in enumerate(recent_items):
            idx = start_idx + offset
            if it.get("id"):
                drop_row.append(InlineKeyboardButton(f"❌ #{idx}", callback_data=f"batch:drop:{it['id']}"))
        if drop_row:
            keyboard.append(drop_row)

    # 5. Secondary Actions Row (Quick, Refresh, Clear)
    secondary_row = []
    if is_admin and items:
        secondary_row.append(InlineKeyboardButton(f"⚡ Quick ({count})", callback_data=f"batch:quick:{batch_id}"))

    secondary_row.append(InlineKeyboardButton("🔄 Refresh", callback_data=f"batch:refresh:{batch_id}"))
    if items:
        secondary_row.append(InlineKeyboardButton("🗑️ Clear All", callback_data=f"batch:clear:{batch_id}"))

    keyboard.append(secondary_row)
    return "\n".join(lines), InlineKeyboardMarkup(keyboard)
