import os
import json
import shutil
import asyncio
import logging
import aiohttp
from pathlib import Path
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import filters, MessageHandler, ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main() -> None:
    _ = load_dotenv()
    telegram_token: str | None = os.getenv("BOT_TOKEN")
    if not telegram_token:
        exit(-1)
    application = ApplicationBuilder().token(telegram_token).build()
    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    main()
