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
import time
from issue_bot.core.database import Database

logger = logging.getLogger(__name__)

SPINNER_FRAMES = ["⚡", "🔄", "⚙️", "✨"]

async def run_with_stepped_progress(
    status_msg,
    coro,
    steps: list[str],
    interval: float = 4.0
) -> Any:
    """
    Run an async coroutine while continuously cycling the status message with:
    1. Progressive architectural phases (steps).
    2. Dynamic live elapsed timer (⏱️ mm:ss).
    3. Pulsing animated spinner frames (⚡, 🔄, ⚙️, ✨).
    Runs indefinitely until the coroutine finishes, preventing UI freeze illusions.
    """
    start_time = time.monotonic()

    async def _ticker():
        idx = 0
        tick_count = 0
        try:
            while True:
                await asyncio.sleep(interval)
                tick_count += 1
                elapsed = int(time.monotonic() - start_time)
                mins, secs = divmod(elapsed, 60)
                timer_str = f"{mins:02d}:{secs:02d}"
                spinner = SPINNER_FRAMES[tick_count % len(SPINNER_FRAMES)]

                if steps:
                    if idx < len(steps):
                        base_step = steps[idx]
                        idx += 1
                    else:
                        base_step = steps[-1]
                else:
                    base_step = "🤖 *AI Issue Engine — Analyzing & Synthesizing...* ⏳"

                footer_lines = [
                    "",
                    f"⏱️ *Elapsed Time*: `{timer_str}` {spinner}",
                ]
                if elapsed >= 20:
                    footer_lines.append("_Processing actively continues, please hold..._")
                if elapsed >= 45:
                    footer_lines.append("💡 _Large batches undergo multi-component architectural clustering._")

                full_text = f"{base_step}\n" + "\n".join(footer_lines)

                try:
                    await status_msg.edit_text(full_text, parse_mode=ParseMode.MARKDOWN)
                except Exception as ex:
                    logger.debug(f"Progress edit notice: {ex}")
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
