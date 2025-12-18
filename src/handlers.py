import logging

from telegram import Sticker, Update
from telegram.ext import ContextTypes

from manager import StickerPackManager

logger: logging.Logger = logging.getLogger(__name__)

async def handle_sticker_pack(update: Update, context: ContextTypes.DEFAULT_TYPE, manager: StickerPackManager) -> None:
    if update.message and update.message.sticker:
        sticker: Sticker = update.message.sticker
        logger.info(f"Received sticker from pack: {sticker.set_name}")
        _ = await update.message.reply_text(f"Processing sticker pack: {sticker.set_name}...")
        await manager.process_sticker_pack(sticker, context)
        _ = await update.message.reply_text("Sticker pack processed successfully!")
