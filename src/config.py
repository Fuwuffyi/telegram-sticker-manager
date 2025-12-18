import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
_ = load_dotenv()

# Paths
DOWNLOAD_DIR: Path = Path("sticker_packs")
REGISTRY_FILE: Path = Path("sticker_registry.json")

# Telegram Bot Token
BOT_TOKEN: str | None = os.getenv("BOT_TOKEN")

def validate_config() -> bool:
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN not found in environment variables")
        return False
    return True
