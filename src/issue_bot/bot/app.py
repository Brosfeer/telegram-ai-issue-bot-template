import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from issue_bot.config import settings
from issue_bot.bot.helpers import set_bot_commands
from issue_bot.bot.handlers import (
    start_command,
    menu_command,
    help_command,
    batch_command,
    clear_command,
    recent_command,
    status_command,
    trigger_ai_command,
    trigger_quick_command,
    users_command,
    pending_command,
    revoke_command,
    photo_handler,
    document_handler,
    text_handler,
    callback_query_handler,
)

logger = logging.getLogger(__name__)

def create_application() -> Application:
    """Build and configure the Telegram Application."""
    if not settings.TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment or .env file.")

    app = (
        Application.builder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .post_init(set_bot_commands)
        .build()
    )

    # Command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("batch", batch_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("ai", trigger_ai_command))
    app.add_handler(CommandHandler("quick", trigger_quick_command))
    app.add_handler(CommandHandler("recent", recent_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("pending", pending_command))
    app.add_handler(CommandHandler("revoke", revoke_command))

    # Media and message handlers
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.Document.IMAGE, document_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    # Callback query handler
    app.add_handler(CallbackQueryHandler(callback_query_handler))

    return app

def main() -> None:
    """Entrypoint to run the Telegram bot polling daemon."""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    )
    logger.info("Starting Telegram AI Issue Bot...")
    app = create_application()
    app.run_polling()

if __name__ == "__main__":
    main()
