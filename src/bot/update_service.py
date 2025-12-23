import asyncio
import logging
from pathlib import Path

from telegram.ext import ContextTypes, Application
from telegram.ext import CallbackContext

from src.bot.manager import StickerPackManager
from src.config import BOT_TOKEN
from src.database import Database

logger: logging.Logger = logging.getLogger(__name__)

class UpdateService:
    def __init__(self, download_dir: Path, db: Database) -> None:
        self.download_dir: Path = download_dir
        self.db: Database = db
        self.manager: StickerPackManager = StickerPackManager(download_dir, db)
        self._app = None

    async def _get_application(self):
        if self._app is None:
            self._app = Application.builder().token(BOT_TOKEN or "").build()
            await self._app.initialize()
        return self._app

    async def update_pack(self, pack_name: str, context = None) -> bool:
        try:
            logger.info(f"Starting update for pack: {pack_name}")
            app = await self._get_application()
            # Get the pack info to fetch first sticker
            pack_info = self.db.get_sticker_pack(pack_name)
            if not pack_info:
                logger.error(f"Pack not found: {pack_name}")
                return False
            # Get first sticker from pack to trigger update
            stickers, _ = self.db.get_pack_stickers(pack_name, page=1, per_page=1)
            if not stickers:
                logger.error(f"No stickers found in pack: {pack_name}")
                return False
            # Get sticker from Telegram
            sticker = await app.bot.get_file(stickers[0]['file_id'])
            # Fetch full sticker object
            telegram_sticker = await app.bot.get_sticker_set(pack_name)
            if telegram_sticker and telegram_sticker.stickers:
                # Use manager to process the pack
                ctx = context if context else _create_context(app)
                await self.manager.process_sticker_pack(
                    telegram_sticker.stickers[0],
                    ctx
                )
                logger.info(f"Successfully updated pack: {pack_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating pack {pack_name}: {e}", exc_info=True)
            return False

    async def update_all_packs(self) -> dict[str, bool]:
        results = {}
        # Get all packs
        packs, _ = self.db.search_sticker_packs("", page=1, per_page=10000)
        logger.info(f"Starting update for {len(packs)} packs")
        app = await self._get_application()
        context = _create_context(app)
        for pack in packs:
            pack_name: str = pack['name']
            success: bool = await self.update_pack(pack_name, context)
            results[pack_name] = success
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)
        successful: int = sum(1 for v in results.values() if v)
        logger.info(f"Update complete: {successful}/{len(results)} packs updated successfully")
        return results

    async def cleanup(self) -> None:
        if self._app:
            await self._app.shutdown()
            self._app = None


def _create_context(app: Application) -> ContextTypes.DEFAULT_TYPE:
    # Create a minimal context
    context = CallbackContext(application=app)
    return context
