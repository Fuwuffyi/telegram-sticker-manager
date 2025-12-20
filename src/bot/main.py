import logging
from functools import partial

from telegram.ext import ApplicationBuilder, MessageHandler, filters

from src.bot.handlers import handle_sticker_pack
from src.bot.manager import StickerPackManager
from src.config import BOT_TOKEN, DATABASE_FILE, DOWNLOAD_DIR, validate_config
from src.database import Database

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger: logging.Logger = logging.getLogger(__name__)

def main() -> None:
    # Validate configuration
    if not validate_config():
        logger.error("Configuration validation failed")
        exit(-1)
    # Create download directory
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    # Initialize database
    db: Database = Database(DATABASE_FILE)
    logger.info(f"Database initialized at {DATABASE_FILE}")
    # Initialize sticker pack manager
    manager: StickerPackManager = StickerPackManager(DOWNLOAD_DIR, db)
    # Build Telegram bot application
    application = ApplicationBuilder().token(BOT_TOKEN or "").build()
    # Create handler with manager bound to it
    sticker_handler = MessageHandler(
        filters.Sticker.ALL,
        partial(handle_sticker_pack, manager=manager)
    )
    # Register handler
    application.add_handler(sticker_handler)
    logger.info("Bot started successfully")
    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    main()
