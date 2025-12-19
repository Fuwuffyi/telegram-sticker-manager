import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
_ = load_dotenv()

# Paths
PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
DOWNLOAD_DIR: Path = PROJECT_ROOT / "sticker_registry" / "pack_files"
REGISTRY_FILE: Path = PROJECT_ROOT / "sticker_registry" / "registry.json"

# Telegram Bot Token
BOT_TOKEN: str | None = os.getenv("BOT_TOKEN")

def validate_config() -> bool:
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN not found in environment variables")
        return False
    return True
