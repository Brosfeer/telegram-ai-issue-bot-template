import asyncio
import logging
from typing import Any
from telegram import (
    Update,
    BotCommand,
    BotCommandScopeDefault,
    BotCommandScopeChat,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, Application
from issue_bot.config import settings
from issue_bot.core.database import Database

logger = logging.getLogger(__name__)

async def run_with_stepped_progress(
    status_msg,
    coro,
    steps: list[str],
    interval: float = 3.5
) -> Any:
    """Run an async coroutine while cycling status message through stepped phases."""
    async def _ticker():
        idx = 0
        try:
            while idx < len(steps):
                await asyncio.sleep(interval)
                try:
                    await status_msg.edit_text(steps[idx], parse_mode=ParseMode.MARKDOWN)
                except Exception:
                    pass
                idx += 1
        except asyncio.CancelledError:
            pass

    ticker_task = asyncio.create_task(_ticker())
    try:
        return await coro
    finally:
        ticker_task.cancel()

async def ensure_authorized_or_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is authorized. If not, record request and alert admin."""
    user = update.effective_user
    if not user:
        return False

    if settings.is_user_authorized(user.id):
        return True

    # Record access request
    Database.record_access_request(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name
    )

    waiting_text = (
        f"🔒 *Access Restricted / صلاحية الوصول مقيدة*\n\n"
        f"Hello {user.first_name}! You need authorization to use this bot.\n"
        f"An access request has been sent to the Admin.\n\n"
        f"🆔 `User ID`: `{user.id}`"
    )
    if update.message:
        await update.message.reply_text(waiting_text, parse_mode=ParseMode.MARKDOWN)
    elif update.callback_query:
        await update.callback_query.answer("Access restricted. Request submitted.", show_alert=True)

    # Notify admin
    admin_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"auth:approve:{user.id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"auth:reject:{user.id}")
        ]
    ])
    uname = f"@{user.username}" if user.username else "No username"
    admin_alert = (
        f"🔔 *New Access Request*\n\n"
        f"👤 *User*: {user.first_name} ({uname})\n"
        f"🆔 *ID*: `{user.id}`\n\n"
        f"Grant access?"
    )
    try:
        await context.bot.send_message(
            chat_id=settings.ADMIN_USER_ID,
            text=admin_alert,
            reply_markup=admin_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.warning(f"Failed to send admin notification: {e}")

    return False

async def set_bot_commands(application: Application) -> None:
    """Register scoped Telegram commands for QA testers and Admin."""
    qa_commands = [
        BotCommand("start", "Start bot & initialize menu"),
        BotCommand("ai", "🤖 Trigger AI to craft issue"),
        BotCommand("batch", "View current staging batch"),
        BotCommand("clear", "Clear active staging batch"),
        BotCommand("menu", "Restore docked persistent keyboard"),
        BotCommand("help", "How to submit feedback & bugs")
    ]
    await application.bot.set_my_commands(qa_commands, scope=BotCommandScopeDefault())

    admin_commands = [
        BotCommand("start", "Start bot & initialize menu"),
        BotCommand("ai", "🤖 Trigger AI to craft issue"),
        BotCommand("batch", "View current staging batch"),
        BotCommand("quick", "⚡ Create 1-click issue from batch"),
        BotCommand("recent", "📋 View recent repository issues"),
        BotCommand("status", "📊 Check repository status"),
        BotCommand("users", "👥 Admin: List authorized team members"),
        BotCommand("pending", "⏳ Admin: View pending access requests"),
        BotCommand("revoke", "🚫 Admin: Revoke user access"),
        BotCommand("clear", "Clear active staging batch"),
        BotCommand("menu", "Restore docked persistent keyboard"),
        BotCommand("help", "Help and documentation")
    ]
    try:
        await application.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=settings.ADMIN_USER_ID))
    except Exception as e:
        logger.warning(f"Could not register admin commands scope for chat {settings.ADMIN_USER_ID}: {e}")

    logger.info("Scoped native bot commands registered successfully.")
