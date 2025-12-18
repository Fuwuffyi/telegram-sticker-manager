import os
import json
import logging
import datetime
from dataclasses import dataclass

from dotenv import load_dotenv

from pathlib import Path
import asyncio
import aiohttp

from telegram import Sticker, StickerSet, Update
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

class StickerPackManager:
    def __init__(self, download_dir: Path, registry_file: Path) -> None:
        self.download_dir: Path = download_dir
        self.registry_file: Path = registry_file
        self.registry: dict[str, dict] = {}
        self._lock: asyncio.Lock = asyncio.Lock()
        self._load_registry()

    def _load_registry(self) -> None:
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    self.registry = json.load(f)
                logger.info(f"Loaded registry with {len(self.registry)} packs")
            except Exception as e:
                logger.error(f"Error loading registry: {e}")
                self.registry = {}
        else:
            self.registry = {}

    async def _save_registry(self) -> None:
        async with self._lock:
            try:
                self.registry_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.registry_file, 'w', encoding='utf-8') as f:
                    json.dump(self.registry, f, indent=2, ensure_ascii=False)
                logger.info("Registry saved successfully")
            except Exception as e:
                logger.error(f"Error saving registry: {e}")

    def _get_pack_dir(self, pack_name: str) -> Path:
        pack_dir: Path = self.download_dir / pack_name
        pack_dir.mkdir(parents=True, exist_ok=True)
        return pack_dir

    async def _download_sticker(self, session: aiohttp.ClientSession, file_url: str,output_path: Path) -> bool:
        try:
            async with session.get(file_url) as response:
                if response.status == 200:
                    content: bytes = await response.read()
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    _ = await asyncio.to_thread(output_path.write_bytes, content)
                    return True
                else:
                    logger.error(f"Failed to download {file_url}: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Error downloading sticker: {e}")
            return False

    def _get_existing_stickers(self, pack_name: str) -> set[str]:
        if pack_name in self.registry:
            return set(self.registry[pack_name].get('stickers', {}).keys())
        return set()

    async def process_sticker_pack(self, sticker: Sticker, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not sticker.set_name:
            logger.warning("Sticker has no set name, skipping")
            return
        pack_name: str = sticker.set_name
        try:
            # Get the full sticker set
            sticker_set: StickerSet = await context.bot.get_sticker_set(pack_name)
            # TODO: Improve sticker count with update timestamp
            # Check if we need to update
            pack_info: dict | None = self.registry.get(pack_name)
            existing_stickers: set[str] = self._get_existing_stickers(pack_name)
            # Create set of current sticker unique IDs
            current_sticker_ids: set[str] = {s.file_unique_id for s in sticker_set.stickers}
            # Check if pack has new stickers
            new_stickers: set[str] = current_sticker_ids - existing_stickers
            if pack_info and not new_stickers:
                logger.info(f"Pack '{pack_name}' is up to date, skipping")
                return
            logger.info(f"Processing pack '{pack_name}' ({sticker_set.title})")
            logger.info(f"New stickers to download: {len(new_stickers)}")
            pack_dir: Path = self._get_pack_dir(pack_name)
            # Prepare sticker info dict (preserve old stickers)
            stickers_dict = pack_info.get('stickers', {}) if pack_info else {}
            # Create emoji mapping file
            emoji_mapping = {}
            # Download new stickers concurrently
            async with aiohttp.ClientSession() as session:
                download_tasks = []
                for stk in sticker_set.stickers:
                    # Add to emoji mapping
                    emoji_mapping[stk.file_unique_id] = stk.emoji or ""
                    # Skip if already downloaded
                    if stk.file_unique_id in existing_stickers:
                        continue
                    # Get file extension
                    if stk.is_animated:
                        ext = "tgs"
                    elif stk.is_video:
                        ext = "webm"
                    else:
                        ext = "webp"
                    # Prepare file info
                    filename = f"{stk.file_unique_id}.{ext}"
                    file_path = pack_dir / filename
                    # Get download URL
                    file = await context.bot.get_file(stk.file_id)
                    # Create download task
                    download_tasks.append(
                        self._download_and_track(
                            session, 
                            file.file_path, 
                            file_path,
                            stk,
                            stickers_dict,
                            filename
                        )
                    )
                # Download all new stickers concurrently
                if download_tasks:
                    await asyncio.gather(*download_tasks)
            # Save emoji mapping
            emoji_file = pack_dir / "emojis.json"
            await asyncio.to_thread(
                emoji_file.write_text,
                json.dumps(emoji_mapping, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            # Update registry
            self.registry[pack_name] = {
                'name': pack_name,
                'title': sticker_set.title,
                'last_update': int(datetime.now().timestamp()),
                'sticker_count': len(stickers_dict),
                'stickers': stickers_dict
            }
            await self._save_registry()
            logger.info(f"Successfully processed pack '{pack_name}'")
        except Exception as e:
            logger.error(f"Error processing sticker pack '{pack_name}': {e}", exc_info=True)

    async def _download_and_track(self, session: aiohttp.ClientSession, file_url: str, output_path: Path, sticker: Sticker, stickers_dict: dict, filename: str) -> None:
        success: bool = await self._download_sticker(session, file_url, output_path)
        if success:
            stickers_dict[sticker.file_unique_id] = {
                'file_id': sticker.file_id,
                'file_unique_id': sticker.file_unique_id,
                'emoji': sticker.emoji,
                'width': sticker.width,
                'height': sticker.height,
                'is_animated': sticker.is_animated,
                'is_video': sticker.is_video,
                'file_path': filename
            }
            logger.info(f"Downloaded: {filename}")

# Global manager instance
manager: StickerPackManager = StickerPackManager(DOWNLOAD_DIR, REGISTRY_FILE)

async def handle_sticker_pack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message and update.message.sticker:
        sticker: Sticker = update.message.sticker
        logger.info(f"Received sticker from pack: {sticker.set_name}")
        _ = await update.message.reply_text(f"Processing sticker pack: {sticker.set_name}...")
        await manager.process_sticker_pack(sticker, context)
        _ = await update.message.reply_text(f"Sticker pack processed successfully!")

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
