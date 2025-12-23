from pathlib import Path

from signalstickers_client import StickersClient
from signalstickers_client.models import LocalStickerPack, Sticker

from src.config import DOWNLOAD_DIR, SIGNAL_UUID, SIGNAL_PASSWORD
from src.database import CustomPackRecord, Database, StickerPackRecord

async def upload_telegram_pack_to_signal(db: Database, pack_name: str) -> str | None:
    pack_info: StickerPackRecord | None = db.get_sticker_pack(pack_name)
    if not pack_info:
        return None
    # Get all stickers for this pack
    stickers_data, _ = db.get_pack_stickers(pack_name, page=1, per_page=10000)
    if not stickers_data:
        return None
    pack_dir: Path = DOWNLOAD_DIR / pack_name
    if not pack_dir.exists():
        return None
    # Create Signal pack
    pack: LocalStickerPack = LocalStickerPack()
    # Signal has a 30 char limit
    pack.title = pack_info['title'][:30]
    pack.author = pack_info['artist'][:30]
    # Add stickers
    for sticker_data in stickers_data:
        sticker_path: Path = pack_dir / sticker_data['file_path']
        if not sticker_path.exists():
            continue
        sticker: Sticker = Sticker()
        sticker.id = sticker_data['display_order']
        sticker.emoji = sticker_data['emoji'][0] if sticker_data['emoji'] else '📷'
        try:
            with open(sticker_path, 'rb') as f:
                sticker.image_data = f.read()
            pack._addsticker(sticker)
        except Exception:
            continue
    if pack.nb_stickers == 0:
        return None
    # Set cover image (first sticker)
    cover: Sticker = Sticker()
    cover.id = pack.nb_stickers
    cover.image_data = pack.stickers[0].image_data[:]
    pack.cover = cover
    # Upload to Signal
    if not SIGNAL_UUID or not SIGNAL_PASSWORD:
        raise ValueError("SIGNAL_UUID and SIGNAL_PASSWORD must be set in environment")
    try:
        async with StickersClient(SIGNAL_UUID, SIGNAL_PASSWORD) as client:
            pack_id, pack_key = await client.upload_pack(pack)
        return f"https://signal.art/addstickers/#pack_id={pack_id}&pack_key={pack_key}"
    except Exception:
        return None

async def upload_custom_pack_to_signal(db: Database, pack_name: str) -> str | None:
    pack_info: CustomPackRecord | None = db.get_custom_pack(pack_name)
    if not pack_info:
        return None
    # Get all stickers for this custom pack
    stickers_data, _ = db.get_custom_pack_stickers(pack_name, page=1, per_page=10000)
    if not stickers_data:
        return None
    # Create Signal pack
    pack: LocalStickerPack = LocalStickerPack()
    # Signal has a 30 char limit
    pack.title = pack_info['title'][:30]
    pack.author = "Custom Pack"[:30]
    # Add stickers from various source packs in order
    for sticker_data in stickers_data:
        pack_dir: Path = DOWNLOAD_DIR / sticker_data['pack_name']
        sticker_path: Path = pack_dir / sticker_data['file_path']
        if not sticker_path.exists():
            continue
        sticker: Sticker = Sticker()
        sticker.id = sticker_data['display_order']
        sticker.emoji = sticker_data['emoji'][0] if sticker_data['emoji'] else '📷'
        try:
            with open(sticker_path, 'rb') as f:
                sticker.image_data = f.read()
            pack._addsticker(sticker)
        except Exception:
            continue
    if pack.nb_stickers == 0:
        return None
    # Set cover image (first sticker)
    cover: Sticker = Sticker()
    cover.id = pack.nb_stickers
    cover.image_data = pack.stickers[0].image_data[:]
    pack.cover = cover
    # Upload to Signal
    if not SIGNAL_UUID or not SIGNAL_PASSWORD:
        raise ValueError("SIGNAL_UUID and SIGNAL_PASSWORD must be set in environment")
    try:
        async with StickersClient(SIGNAL_UUID, SIGNAL_PASSWORD) as client:
            pack_id, pack_key = await client.upload_pack(pack)
        return f"https://signal.art/addstickers/#pack_id={pack_id}&pack_key={pack_key}"
    except Exception:
        return None
