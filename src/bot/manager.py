import asyncio
import logging
from datetime import datetime
from pathlib import Path

import aiohttp
from telegram import File, Sticker, StickerSet
from telegram.ext import ContextTypes

from src.database import Database, StickerRecord

logger: logging.Logger = logging.getLogger(__name__)

class StickerPackManager:
    def __init__(self, download_dir: Path, db: Database) -> None:
        self.download_dir: Path = download_dir
        self.db: Database = db
        self._lock: asyncio.Lock = asyncio.Lock()

    def _get_pack_dir(self, pack_name: str) -> Path:
        pack_dir: Path = self.download_dir / pack_name
        pack_dir.mkdir(parents=True, exist_ok=True)
        return pack_dir

    async def _download_sticker(self, session: aiohttp.ClientSession, file_url: str, output_path: Path) -> bool:
        try:
            async with session.get(file_url) as response:
                if response.status == 200:
                    content: bytes = await response.read()
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    _ = await asyncio.to_thread(output_path.write_bytes, content)
                    return True
                logger.error(f"Failed to download {file_url}: {response.status}")
                return False
        except Exception as e:
            logger.error(f"Error downloading sticker: {e}")
            return False

    def _get_file_extension(self, sticker: Sticker) -> str:
        if sticker.is_animated:
            return "tgs"
        elif sticker.is_video:
            return "webm"
        return "webp"

    async def _download_and_track(self, session: aiohttp.ClientSession, file_url: str, output_path: Path, sticker: Sticker) -> StickerRecord | None:
        success: bool = await self._download_sticker(session, file_url, output_path)
        if success:
            sticker_record: StickerRecord = {
                'file_id': sticker.file_id,
                'file_unique_id': sticker.file_unique_id,
                'emoji': sticker.emoji,
                'file_path': output_path.name
            }
            logger.info(f"Downloaded: {output_path.name}")
            return sticker_record
        return None

    async def process_sticker_pack(self, sticker: Sticker, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not sticker.set_name:
            logger.warning("Sticker has no set name, skipping")
            return
        pack_name: str = sticker.set_name
        try:
            # Get the full sticker set
            sticker_set: StickerSet = await context.bot.get_sticker_set(pack_name)
            logger.info(f"Retrieved sticker set: {sticker_set.title}")
            # Check if we need to update
            existing_stickers: set[str] = self.db.get_sticker_unique_ids(pack_name)
            current_sticker_ids: set[str] = {s.file_unique_id for s in sticker_set.stickers}
            # Check if pack has new stickers
            new_stickers: set[str] = current_sticker_ids - existing_stickers
            removed_stickers: set[str] = existing_stickers - current_sticker_ids
            if not new_stickers and not removed_stickers and existing_stickers:
                logger.info(f"Pack '{pack_name}' is up to date with {len(existing_stickers)} stickers, skipping")
                return
            logger.info(f"Processing pack '{pack_name}' ({sticker_set.title})")
            if existing_stickers:
                logger.info(f"New stickers to download: {len(new_stickers)}")
            else:
                logger.info(f"First time download: {len(current_sticker_ids)} stickers")
            pack_dir: Path = self._get_pack_dir(pack_name)
            # Update pack info in database
            pack_artist: str = 'Unknown'
            existing_pack = self.db.get_sticker_pack(pack_name)
            if existing_pack:
                pack_artist = existing_pack['artist']
            async with self._lock:
                self.db.upsert_sticker_pack({
                    'name': pack_name,
                    'title': sticker_set.title,
                    'artist': pack_artist,
                    'last_update': int(datetime.now().timestamp()),
                    'sticker_count': len(current_sticker_ids)
                })
            # Download new stickers concurrently
            async with aiohttp.ClientSession() as session:
                download_tasks: list[asyncio.Task[StickerRecord | None]] = []
                for stk in sticker_set.stickers:
                    # Skip if already downloaded
                    if stk.file_unique_id in existing_stickers:
                        continue
                    # Get file extension
                    ext: str = self._get_file_extension(stk)
                    # Prepare file info
                    filename: str = f"{stk.file_unique_id}.{ext}"
                    file_path: Path = pack_dir / filename
                    # Get download URL
                    file: File = await context.bot.get_file(stk.file_id)
                    # Create download task
                    task: asyncio.Task[StickerRecord | None] = asyncio.create_task(
                        self._download_and_track(session, file.file_path or "", file_path, stk)
                    )
                    download_tasks.append(task)
                # Download all new stickers concurrently
                if download_tasks:
                    downloaded_stickers: list[StickerRecord | None] = await asyncio.gather(*download_tasks)
                    # Save to database
                    async with self._lock:
                        for sticker_record in downloaded_stickers:
                            if sticker_record:
                                self.db.upsert_sticker(pack_name, sticker_record)
            logger.info(f"Successfully processed pack '{pack_name}'")
        except Exception as e:
            logger.error(f"Error processing sticker pack '{pack_name}': {e}", exc_info=True)
