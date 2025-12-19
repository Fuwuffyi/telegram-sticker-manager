import logging

from telegram import Message, Sticker, Update
from telegram.ext import ContextTypes

from src.bot.manager import StickerPackManager

logger: logging.Logger = logging.getLogger(__name__)

async def handle_sticker_pack(update: Update, context: ContextTypes.DEFAULT_TYPE, manager: StickerPackManager) -> None:
    if not update.message or not update.message.sticker:
        return
    message: Message = update.message
    sticker: Sticker = message.sticker  # pyright: ignore[reportAssignmentType]
    logger.info(f"Received sticker from pack: {sticker.set_name}")
    _ = await update.message.reply_text(f"Processing sticker pack: {sticker.set_name}...")
    await manager.process_sticker_pack(sticker, context)
    _ = await update.message.reply_text("Sticker pack processed successfully!")
