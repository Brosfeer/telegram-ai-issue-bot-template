import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from issue_bot.config import settings
from issue_bot.core.database import Database
from datetime import datetime, timezone
from pathlib import Path
from issue_bot.bot.keyboards import AI_PROGRESS_STEPS, format_batch_card
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

    # Single isolated item trigger: single:ai:<item_id>
    if data.startswith("single:ai:"):
        item_id = int(data.split(":")[2])
        item = Database.get_item(item_id)
        if not item:
            await query.edit_message_text("⚠️ Item not found or already processed.")
            return

        try:
            new_batch_id = Database.isolate_items_to_new_batch(
                user_id=user.id,
                item_ids=[item_id],
                title=f"Isolated Issue - Item #{item_id}"
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Failed to isolate item: `{e}`", parse_mode=ParseMode.MARKDOWN)
            return

        if not Database.lock_batch_for_processing(new_batch_id):
            await query.edit_message_text("⏳ Item is already being processed.")
            return

        try:
            await query.edit_message_text(AI_PROGRESS_STEPS[0], parse_mode=ParseMode.MARKDOWN)
            result = await run_with_stepped_progress(
                query.message,
                create_ai_issue_from_batch(new_batch_id),
                AI_PROGRESS_STEPS,
                interval=4.0
            )
        except Exception as e:
            Database.unlock_batch(new_batch_id)
            await query.edit_message_text(f"❌ Error: `{e}`", parse_mode=ParseMode.MARKDOWN)
            return

        if result.get("success"):
            iss_num = result.get("issue_number")
            iss_url = result.get("issue_url")
            await query.edit_message_text(
                f"✅ *Isolated Issue #{iss_num} Published!*\n\n🔗 [Open on GitHub]({iss_url})",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            err = result.get("error", "Unknown error")
            await query.edit_message_text(f"❌ *Failed*: `{err}`", parse_mode=ParseMode.MARKDOWN)
        return

    # Staging batch actions
    if data.startswith("batch:"):
        parts = data.split(":")
        action = parts[1]
        target_id = int(parts[2])

        # Drop individual item: batch:drop:<item_id>
        if action == "drop":
            item = Database.delete_batch_item(target_id)
            if item and item.get("local_path"):
                Path(item["local_path"]).unlink(missing_ok=True)
            batch = Database.get_open_batch(user.id)
            if not batch:
                await query.edit_message_text("ℹ️ Batch is empty.")
                return
            items = Database.get_batch_items(batch["id"])
            card_text, reply_markup = format_batch_card(batch, items, user.id)
            await query.edit_message_text(card_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            return

        batch_id = target_id

        if action == "refresh":
            batch = Database.get_open_batch(user.id)
            if not batch:
                await query.edit_message_text("ℹ️ No active batch found.")
                return
            items = Database.get_batch_items(batch["id"])
            card_text, reply_markup = format_batch_card(batch, items, user.id)
            try:
                await query.edit_message_text(card_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            except Exception:
                pass
            return

        if action == "clear":
            Database.clear_batch(user.id)
            await query.edit_message_text("🗑️ Staging batch cleared.")
            return

        # Date-scoped trigger: batch:today:<batch_id>
        if action == "today":
            batch = Database.get_batch(batch_id)
            if not batch:
                await query.edit_message_text("⚠️ Batch not found.")
                return
            items = Database.get_batch_items(batch_id)
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            today_item_ids = [it["id"] for it in items if str(it.get("created_at", ""))[:10] == today_str]
            if not today_item_ids:
                await query.edit_message_text("⚠️ No items from today found in batch.")
                return

            try:
                isolated_batch_id = Database.isolate_items_to_new_batch(
                    user_id=user.id,
                    item_ids=today_item_ids,
                    title=f"Today QA Items - Batch #{batch_id}"
                )
            except Exception as e:
                await query.edit_message_text(f"❌ Failed to isolate today's items: `{e}`", parse_mode=ParseMode.MARKDOWN)
                return

            if not Database.lock_batch_for_processing(isolated_batch_id):
                await query.edit_message_text("⏳ Batch is already being processed.")
                return

            try:
                await query.edit_message_text(AI_PROGRESS_STEPS[0], parse_mode=ParseMode.MARKDOWN)
                result = await run_with_stepped_progress(
                    query.message,
                    create_ai_issue_from_batch(isolated_batch_id),
                    AI_PROGRESS_STEPS,
                    interval=4.0
                )
            except Exception as e:
                Database.unlock_batch(isolated_batch_id)
                await query.edit_message_text(f"❌ Error: `{e}`", parse_mode=ParseMode.MARKDOWN)
                return

            if result.get("success"):
                iss_num = result.get("issue_number")
                iss_url = result.get("issue_url")
                await query.edit_message_text(
                    f"✅ *Issue #{iss_num} Published (Today's Items)!*\n\n🔗 [Open on GitHub]({iss_url})",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                err = result.get("error", "Unknown error")
                await query.edit_message_text(f"❌ *Failed*: `{err}`", parse_mode=ParseMode.MARKDOWN)
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
                    interval=4.0
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
