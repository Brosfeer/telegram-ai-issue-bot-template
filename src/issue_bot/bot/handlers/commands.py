import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from issue_bot.config import settings
from issue_bot.core.database import Database
from issue_bot.bot.keyboards import get_persistent_keyboard, format_batch_card, AI_PROGRESS_STEPS
from issue_bot.bot.helpers import (
    ensure_authorized_or_request,
    run_with_stepped_progress
)
from issue_bot.services.github_service import get_repo_recent_issues, get_repo_status_summary
from issue_bot.services.quick_issue_service import create_quick_issue_from_batch
from issue_bot.services.ai_service import create_ai_issue_from_batch

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_authorized_or_request(update, context):
        return

    user = update.effective_user
    text = (
        f"👋 *Welcome {user.first_name} to Telegram AI Issue Bot!*\n\n"
        f"✨ Seamless GitHub Issue reporting and automated triage from Telegram.\n\n"
        f"🎯 *Workflow:*\n"
        f"1. 📥 Send screenshots or technical notes.\n"
        f"2. 🤖 Tap `[ 🤖 Trigger AI Issue ]` for automated codebase triage and GitHub authoring.\n"
        f"3. ⚡ Or tap `[ ⚡ Quick Issue ]` for instantaneous 1-click publishing.\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📁 *Target Repo*: `{settings.TARGET_REPO_NAME}`\n"
        f"🌿 *Base Branch*: `{settings.TARGET_BASE_BRANCH}`"
    )
    reply_markup = get_persistent_keyboard(user.id)
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_authorized_or_request(update, context):
        return
    user = update.effective_user
    reply_markup = get_persistent_keyboard(user.id)
    await update.message.reply_text("📋 Menu restored.", reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_authorized_or_request(update, context):
        return
    text = (
        "💡 *Telegram AI Issue Bot Guide*\n\n"
        "• **Send Screenshots**: Attach individual photos or entire albums.\n"
        "• **Send Notes**: Type normal messages to document defects or observations.\n"
        "• **/batch**: View your active staging buffer.\n"
        "• **/ai**: Synthesize an issue with AI analysis.\n"
        "• **/quick**: Publish a 1-click issue.\n"
        "• **/clear**: Reset your staging buffer."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def batch_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_authorized_or_request(update, context):
        return
    user = update.effective_user
    batch = Database.get_or_create_open_batch(user.id)
    items = Database.get_batch_items(batch["id"])
    card_text, reply_markup = format_batch_card(batch, items, user.id)
    await update.message.reply_text(card_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_authorized_or_request(update, context):
        return
    user = update.effective_user
    cleared_id = Database.clear_batch(user.id)
    if cleared_id:
        await update.message.reply_text(f"🗑️ Staging batch `#{cleared_id}` has been cleared.", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("ℹ️ No active open batch to clear.")

async def trigger_ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_authorized_or_request(update, context):
        return
    user = update.effective_user
    batch = Database.get_open_batch(user.id)
    if not batch:
        await update.message.reply_text("ℹ️ Your batch is empty. Send screenshots or notes first.")
        return

    items = Database.get_batch_items(batch["id"])
    if not items:
        await update.message.reply_text("ℹ️ Your batch is empty. Send screenshots or notes first.")
        return

    status_msg = await update.message.reply_text(AI_PROGRESS_STEPS[0], parse_mode=ParseMode.MARKDOWN)
    custom_instruction = " ".join(context.args) if context.args else None

    result = await run_with_stepped_progress(
        status_msg,
        create_ai_issue_from_batch(batch["id"], custom_instruction=custom_instruction),
        AI_PROGRESS_STEPS,
        interval=3.0
    )

    if result.get("success"):
        iss_num = result.get("issue_number")
        iss_url = result.get("issue_url")
        await status_msg.edit_text(
            f"✅ *Issue #{iss_num} Created Successfully!*\n\n🔗 [Open on GitHub]({iss_url})",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        err = result.get("error", "Unknown error")
        await status_msg.edit_text(f"❌ *Failed to create issue*: `{err}`", parse_mode=ParseMode.MARKDOWN)

async def trigger_quick_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_authorized_or_request(update, context):
        return
    user = update.effective_user
    if not (user.id == settings.ADMIN_USER_ID or Database.is_admin(user.id)):
        await update.message.reply_text("⛔ Admin only command.")
        return

    batch = Database.get_open_batch(user.id)
    if not batch:
        await update.message.reply_text("ℹ️ Batch is empty.")
        return

    status_msg = await update.message.reply_text("⚡ Creating Quick Issue on GitHub...")
    custom_title = " ".join(context.args) if context.args else None

    result = await create_quick_issue_from_batch(batch["id"], custom_title=custom_title)
    if result.get("success"):
        iss_num = result.get("issue_number")
        iss_url = result.get("issue_url")
        await status_msg.edit_text(
            f"⚡ *Quick Issue #{iss_num} Published!*\n\n🔗 [Open on GitHub]({iss_url})",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        err = result.get("error", "Unknown error")
        await status_msg.edit_text(f"❌ *Failed*: `{err}`", parse_mode=ParseMode.MARKDOWN)

async def recent_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_authorized_or_request(update, context):
        return
    status_msg = await update.message.reply_text("🔍 Fetching recent issues...")
    issues = await get_repo_recent_issues(limit=5)
    if not issues:
        await status_msg.edit_text("ℹ️ No recent open issues found.")
        return

    lines = [f"📋 *Recent Open Issues for {settings.TARGET_REPO_NAME}:*", "━━━━━━━━━━━━━━━━━━━"]
    for iss in issues:
        num = iss.get("number")
        title = iss.get("title")
        url = iss.get("url")
        lines.append(f"• [#{num}: {title}]({url})")
    await status_msg.edit_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_authorized_or_request(update, context):
        return
    status_msg = await update.message.reply_text("📊 Checking repository status...")
    summary = await get_repo_status_summary()
    text = (
        f"📊 *Repository Status*\n"
        f"• *Repo*: `{summary['repo']}`\n"
        f"• *Branch*: `{summary['base_branch']}`\n\n"
        f"```text\n{summary['output'][:800]}\n```"
    )
    await status_msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not Database.is_admin(user.id):
        await update.message.reply_text("⛔ Admin only command.")
        return
    users = Database.get_authorized_users()
    lines = ["👥 *Authorized Team Members:*", "━━━━━━━━━━━━━━━━━━━"]
    for u in users:
        uid = u["user_id"]
        uname = f"@{u['username']}" if u.get("username") else "No username"
        fname = u.get("first_name") or "User"
        role = u.get("role", "qa").upper()
        lines.append(f"• `{uid}` — *{fname}* ({uname}) | `{role}`")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

async def pending_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not Database.is_admin(user.id):
        await update.message.reply_text("⛔ Admin only command.")
        return
    pending = Database.get_pending_requests()
    if not pending:
        await update.message.reply_text("✅ No pending access requests.")
        return
    await update.message.reply_text(f"📋 *Pending Access Requests ({len(pending)}):*", parse_mode=ParseMode.MARKDOWN)
    for req in pending:
        uid = req["user_id"]
        uname = f"@{req['username']}" if req.get("username") else "N/A"
        fname = req.get("first_name") or "User"
        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"auth:approve:{uid}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"auth:reject:{uid}")
            ]
        ])
        await update.message.reply_text(f"👤 *{fname}* ({uname})\n🆔 `{uid}`", parse_mode=ParseMode.MARKDOWN, reply_markup=markup)

async def revoke_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not Database.is_admin(user.id):
        await update.message.reply_text("⛔ Admin only command.")
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("ℹ️ Usage: `/revoke <user_id>`")
        return
    target_uid = int(context.args[0])
    if target_uid == settings.ADMIN_USER_ID:
        await update.message.reply_text("🛡️ Cannot revoke Super Admin.")
        return
    success = Database.revoke_user(target_uid)
    if success:
        await update.message.reply_text(f"🚫 Access revoked for `{target_uid}`.", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"⚠️ User `{target_uid}` not found.")
