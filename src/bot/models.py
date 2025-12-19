from dataclasses import dataclass
from typing import Any

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

    def to_dict(self) -> dict[str, str | int | bool | None]:
        return {
            'file_id': self.file_id,
            'file_unique_id': self.file_unique_id,
            'emoji': self.emoji,
            'width': self.width,
            'height': self.height,
            'is_animated': self.is_animated,
            'is_video': self.is_video,
            'file_path': self.file_path
        }

@dataclass
class StickerPackInfo:
    name: str
    title: str
    artist: str
    last_update: int
    sticker_count: int
    stickers: dict[str, dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            'name': self.name,
            'title': self.title,
            'artist': self.artist,
            'last_update': self.last_update,
            'sticker_count': self.sticker_count,
            'stickers': self.stickers
        }
