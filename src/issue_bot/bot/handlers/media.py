import asyncio
import logging
from pathlib import Path
from typing import Dict, Any
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from issue_bot.config import settings
from issue_bot.core.database import Database
from issue_bot.core.storage import get_target_filepath, inspect_image_file
from issue_bot.bot.keyboards import format_batch_card
from issue_bot.bot.helpers import ensure_authorized_or_request

logger = logging.getLogger(__name__)
_MEDIA_GROUP_TASKS: Dict[str, asyncio.Task] = {}

async def _send_debounced_batch_summary(chat_id: int, user_id: int, batch_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await asyncio.sleep(2.0)
        batch = Database.get_open_batch(user_id)
        if not batch or batch["id"] != batch_id:
            return
        items = Database.get_batch_items(batch_id)
        card_text, reply_markup = format_batch_card(batch, items, user_id)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"📸 *Media Group Processed!*\n\n{card_text}",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error sending debounced batch summary: {e}")

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_authorized_or_request(update, context):
        return

    user = update.effective_user
    msg = update.message
    if not msg.photo:
        return

    photo = msg.photo[-1]
    caption = (msg.caption or "").strip()
    media_group_id = msg.media_group_id

    batch = Database.get_or_create_open_batch(user.id)
    batch_id = batch["id"]

    target_path = get_target_filepath(original_name="telegram_photo.png", ext=".png")
    tg_file = await photo.get_file()
    await tg_file.download_to_drive(custom_path=str(target_path))

    # Fast header forensic validation
    meta = inspect_image_file(target_path)
    if not meta.get("valid"):
        target_path.unlink(missing_ok=True)
        await msg.reply_text("⚠️ Image appears corrupt or unsupported. Please resend.")
        return

    item_id = Database.add_item_to_batch(
        batch_id=batch_id,
        user_id=user.id,
        item_type="image",
        file_id=photo.file_id,
        file_unique_id=photo.file_unique_id,
        local_path=str(target_path),
        caption=caption or None,
        media_group_id=media_group_id
    )

    if media_group_id:
        if media_group_id in _MEDIA_GROUP_TASKS:
            _MEDIA_GROUP_TASKS[media_group_id].cancel()
        task = asyncio.create_task(
            _send_debounced_batch_summary(msg.chat_id, user.id, batch_id, context)
        )
        _MEDIA_GROUP_TASKS[media_group_id] = task
    else:
        items = Database.get_batch_items(batch_id)
        card_text, reply_markup = format_batch_card(batch, items, user.id)
        await msg.reply_text(card_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_authorized_or_request(update, context):
        return

    user = update.effective_user
    doc = update.message.document
    if not doc:
        return

    caption = (update.message.caption or "").strip()
    batch = Database.get_or_create_open_batch(user.id)
    batch_id = batch["id"]

    file_ext = Path(doc.file_name or "document.png").suffix or ".png"
    target_path = get_target_filepath(original_name=doc.file_name, ext=file_ext)
    tg_file = await doc.get_file()
    await tg_file.download_to_drive(custom_path=str(target_path))

    Database.add_item_to_batch(
        batch_id=batch_id,
        user_id=user.id,
        item_type="image",
        file_id=doc.file_id,
        file_unique_id=doc.file_unique_id,
        local_path=str(target_path),
        caption=caption or doc.file_name,
        media_group_id=None
    )

    items = Database.get_batch_items(batch_id)
    card_text, reply_markup = format_batch_card(batch, items, user.id)
    await update.message.reply_text(card_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
