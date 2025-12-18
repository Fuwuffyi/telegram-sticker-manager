import os
import json
import logging
from dataclasses import dataclass

from dotenv import load_dotenv

from pathlib import Path
import asyncio
import aiohttp

from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, ContextTypes

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger: logging.Logger = logging.getLogger(__name__)

# Configuration
DOWNLOAD_DIR: Path = Path("sticker_packs")
REGISTRY_FILE: Path = Path("sticker_registry.json")

@dataclass
class StickerInfo:
    file_id: str
    file_unique_id: str
    emoji: str | None
    width: int
    height: int
    is_animated: bool
    is_video: bool
    file_path: str

@dataclass
class StickerPackInfo:
    name: str
    title: str
    last_update: int
    stickers: dict[str, StickerInfo]

async def handle_sticker_pack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(update)
    print(context)

def main() -> None:
    # Load .env file for tokens
    _ = load_dotenv()
    telegram_token: str | None = os.getenv("BOT_TOKEN")
    if not telegram_token:
        exit(-1)
    # Create download directory
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    # Build telegram bot
    application = ApplicationBuilder().token(telegram_token).build()
    # Register handlers
    handlers = [
        MessageHandler(filters.Sticker.ALL, handle_sticker_pack),
    ]
    for handler in handlers:
        application.add_handler(handler)
    logger.info("Bot started successfully")
    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    main()
