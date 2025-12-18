import os
import json
import logging

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
logger = logging.getLogger(__name__)

async def handle_sticker_pack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(update)
    print(context)

def main() -> None:
    _ = load_dotenv()
    telegram_token: str | None = os.getenv("BOT_TOKEN")
    if not telegram_token:
        exit(-1)
    application = ApplicationBuilder().token(telegram_token).build()
     # Register handlers
    handlers = [
        MessageHandler(filters.Sticker.ALL, handle_sticker_pack),
    ]
    for handler in handlers:
        application.add_handler(handler)
    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    main()
