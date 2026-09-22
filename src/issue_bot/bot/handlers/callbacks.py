import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from issue_bot.config import settings
from issue_bot.core.database import Database
from issue_bot.bot.keyboards import AI_PROGRESS_STEPS
from issue_bot.bot.helpers import run_with_stepped_progress
from issue_bot.services.quick_issue_service import create_quick_issue_from_batch
from issue_bot.services.ai_service import create_ai_issue_from_batch

logger = logging.getLogger(__name__)

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    user = update.effective_user

    # Access request approval
    if data.startswith("auth:"):
        if not Database.is_admin(user.id):
            await query.edit_message_text("⛔ Unauthorized.")
            return

        parts = data.split(":")
        action = parts[1]
        target_uid = int(parts[2])

        if action == "approve":
            Database.authorize_user(
                user_id=target_uid,
                username=None,
                first_name=f"User {target_uid}",
                role="qa",
                authorized_by=user.id
            )
            await query.edit_message_text(f"✅ User `{target_uid}` approved.", parse_mode=ParseMode.MARKDOWN)
            try:
                await context.bot.send_message(
                    chat_id=target_uid,
                    text="🎉 *Your access has been approved!*\nSend `/start` to begin.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception:
                pass
        elif action == "reject":
            Database.resolve_access_request(target_uid, status="rejected")
            await query.edit_message_text(f"❌ User `{target_uid}` access request rejected.", parse_mode=ParseMode.MARKDOWN)
        return

    # Staging batch actions
    if data.startswith("batch:"):
        parts = data.split(":")
        action = parts[1]
        batch_id = int(parts[2])

        if action == "clear":
            Database.clear_batch(user.id)
            await query.edit_message_text("🗑️ Staging batch cleared.")
            return

        if not Database.lock_batch_for_processing(batch_id):
            await query.edit_message_text("⏳ Batch is already being processed.")
            return

        try:
            if action == "ai":
                await query.edit_message_text(AI_PROGRESS_STEPS[0], parse_mode=ParseMode.MARKDOWN)
                result = await run_with_stepped_progress(
                    query.message,
                    create_ai_issue_from_batch(batch_id),
                    AI_PROGRESS_STEPS,
                    interval=3.0
                )
            elif action == "quick":
                await query.edit_message_text("⚡ Creating Quick Issue...")
                result = await create_quick_issue_from_batch(batch_id)
            else:
                Database.unlock_batch(batch_id)
                return
        except Exception as e:
            Database.unlock_batch(batch_id)
            await query.edit_message_text(f"❌ Error: `{e}`", parse_mode=ParseMode.MARKDOWN)
            return

        if result.get("success"):
            iss_num = result.get("issue_number")
            iss_url = result.get("issue_url")
            await query.edit_message_text(
                f"✅ *Issue #{iss_num} Published!*\n\n🔗 [Open on GitHub]({iss_url})",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            err = result.get("error", "Unknown error")
            await query.edit_message_text(f"❌ *Failed*: `{err}`", parse_mode=ParseMode.MARKDOWN)
