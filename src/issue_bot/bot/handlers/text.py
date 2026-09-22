import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from issue_bot.core.database import Database
from issue_bot.bot.keyboards import format_batch_card
from issue_bot.bot.helpers import ensure_authorized_or_request
from issue_bot.services.gatekeeper import check_text_relevance
from issue_bot.bot.handlers.commands import (
    trigger_ai_command,
    trigger_quick_command,
    batch_command,
    recent_command,
    status_command,
    help_command
)

logger = logging.getLogger(__name__)

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_authorized_or_request(update, context):
        return

    user = update.effective_user
    text = (update.message.text or "").strip()
    if not text:
        return

    # Docked keyboard button actions
    if text == "🤖 Trigger AI Issue":
        await trigger_ai_command(update, context)
        return
    elif text == "📦 Current Batch":
        await batch_command(update, context)
        return
    elif text == "⚡ Quick Issue":
        await trigger_quick_command(update, context)
        return
    elif text == "📋 Recent Issues":
        await recent_command(update, context)
        return
    elif text == "📊 Repo Status":
        await status_command(update, context)
        return
    elif text == "❓ Help":
        await help_command(update, context)
        return

    batch = Database.get_or_create_open_batch(user.id)
    batch_id = batch["id"]

    # Auto-adoption: If message is a reply to a previous photo or precedes an uncaptioned photo
    reply_msg = update.message.reply_to_message
    if reply_msg and reply_msg.photo:
        photo = reply_msg.photo[-1]
        target_item = Database.find_item_by_file_unique_id(batch_id, photo.file_unique_id)
        if target_item:
            Database.update_item_caption(target_item["id"], text)
            items = Database.get_batch_items(batch_id)
            card_text, reply_markup = format_batch_card(batch, items, user.id)
            await update.message.reply_text(
                f"🔗 *Note paired with Snapshot #{target_item['id']}!*\n\n{card_text}",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return

    # Check relevance via Gatekeeper
    is_rel, reason = check_text_relevance(text)
    if not is_rel:
        if reason == "conversational_chatter":
            await update.message.reply_text("👋 Hello! Please send actionable QA observations, bug reports, or screenshots.")
            return
        elif reason == "too_short":
            await update.message.reply_text("ℹ️ Note is too short. Please describe the issue in more detail.")
            return

    # Append text note to batch
    Database.add_item_to_batch(
        batch_id=batch_id,
        user_id=user.id,
        item_type="text",
        caption=text
    )

    items = Database.get_batch_items(batch_id)
    card_text, reply_markup = format_batch_card(batch, items, user.id)
    await update.message.reply_text(card_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
