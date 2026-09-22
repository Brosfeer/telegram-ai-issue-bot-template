"""Entrypoint daemon for Telegram AI Issue Bot."""
import logging
import sys

from issue_bot.config import settings
from issue_bot.core.database import Database
from issue_bot.bot.app import create_application

# Structured logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
)
logger = logging.getLogger(__name__)

def main() -> None:
    """Main entry point for bot daemon."""
    logger.info("Initializing Telegram AI Issue Bot...")
    
    # Initialize storage directories and database schema
    settings.init_directories()
    Database.init_db()

    # Build and launch Telegram application polling
    try:
        app = create_application()
        logger.info(f"Bot initialized successfully. Connected to repo: {settings.TARGET_REPO_NAME}")
        app.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.error(f"Fatal error starting bot: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
