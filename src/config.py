import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
_ = load_dotenv()

# Paths
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DOWNLOAD_DIR: Path = PROJECT_ROOT / "sticker_registry" / "pack_files"
DATABASE_FILE: Path = PROJECT_ROOT / "sticker_registry" / "sticker_data.sqlite"

# Telegram Bot Token
BOT_TOKEN: str | None = os.getenv("BOT_TOKEN")
SIGNAL_UUID: str | None = os.getenv("SIGNAL_UUID")
SIGNAL_PASSWORD: str | None = os.getenv("SIGNAL_PASSWORD")

def validate_config() -> bool:
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN not found in environment variables")
        return False
    if not SIGNAL_UUID or not SIGNAL_PASSWORD:
        print("WARN: SIGNAL_UUID or SIGNAL_PASSWORD not found in environment variables.\nSignal uploads may not work.")
    return True
