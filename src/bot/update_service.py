import asyncio
import logging
from pathlib import Path

from telegram.ext import Application, ContextTypes, CallbackContext

from src.bot.manager import StickerPackManager
from src.config import BOT_TOKEN
from src.database import Database

logger = logging.getLogger(__name__)


class UpdateService:
    def __init__(self, download_dir: Path, db: Database) -> None:
        self.download_dir: Path = download_dir
        self.db: Database = db
        self.manager: StickerPackManager = StickerPackManager(download_dir, db)

    async def update_pack(self, pack_name: str) -> bool:
        logger.info(f"Starting update for pack: {pack_name}")
        async with Application.builder().token(BOT_TOKEN or "").build() as app:
            await app.initialize()
            try:
                pack_info = self.db.get_sticker_pack(pack_name)
                if not pack_info:
                    logger.error(f"Pack not found: {pack_name}")
                    return False
                stickers, _ = self.db.get_pack_stickers(
                    pack_name, page=1, per_page=1
                )
                if not stickers:
                    logger.error(f"No stickers found in pack: {pack_name}")
                    return False
                telegram_pack = await app.bot.get_sticker_set(pack_name)
                if not telegram_pack or not telegram_pack.stickers:
                    logger.error(f"Telegram pack empty: {pack_name}")
                    return False
                context = _create_context(app)
                await self.manager.process_sticker_pack(
                    telegram_pack.stickers[0],
                    context
                )
                logger.info(f"Successfully updated pack: {pack_name}")
                return True
            except Exception:
                logger.exception(f"Error updating pack {pack_name}")
                return False

    async def update_all_packs(self) -> dict[str, bool]:
        packs, _ = self.db.search_sticker_packs(
            "", page=1, per_page=10000
        )
        logger.info(f"Starting update for {len(packs)} packs")
        results: dict[str, bool] = {}
        async with Application.builder().token(BOT_TOKEN or "").build() as app:
            await app.initialize()
            context = _create_context(app)
            for pack in packs:
                pack_name = pack["name"]
                try:
                    telegram_pack = await app.bot.get_sticker_set(pack_name)
                    if not telegram_pack or not telegram_pack.stickers:
                        results[pack_name] = False
                        continue
                    await self.manager.process_sticker_pack(
                        telegram_pack.stickers[0],
                        context
                    )
                    results[pack_name] = True
                    await asyncio.sleep(0.5)
                except Exception:
                    logger.exception(f"Error updating pack {pack_name}")
                    results[pack_name] = False

        success_count: int = sum(results.values())
        logger.info(
            f"Update complete: {success_count}/{len(results)} packs updated"
        )

        return results


def _create_context(app) -> ContextTypes.DEFAULT_TYPE:
    return CallbackContext(application=app)
