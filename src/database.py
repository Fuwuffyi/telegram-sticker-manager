import json
import sqlite3
from pathlib import Path
from typing import TypedDict

class StickerRecord(TypedDict):
    file_id: str
    file_unique_id: str
    emoji: str | None
    file_path: str

class StickerPackRecord(TypedDict):
    name: str
    title: str
    artist: str
    last_update: int
    sticker_count: int

class StickerSearchResult(TypedDict):
    pack_name: str
    pack_title: str
    artist: str
    file_unique_id: str
    emoji: str
    file_path: str

class CustomPackSticker(TypedDict):
    pack_name: str
    pack_title: str
    file_unique_id: str
    file_path: str
    emoji: str

class CustomPackRecord(TypedDict):
    name: str
    title: str

class Database:
    def __init__(self, db_path: Path) -> None:
        self.db_path: Path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _connect(self) -> sqlite3.Connection:
        conn: sqlite3.Connection = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        # Enable foreign keys
        _ = conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_database(self) -> None:
        with self._connect() as conn:
            # Sticker packs table
            _ = conn.execute("""
                CREATE TABLE IF NOT EXISTS sticker_packs (
                    name TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    artist TEXT NOT NULL,
                    last_update INTEGER NOT NULL,
                    sticker_count INTEGER NOT NULL
                )
            """)
            # Stickers table
            _ = conn.execute("""
                CREATE TABLE IF NOT EXISTS stickers (
                    pack_name TEXT NOT NULL,
                    file_id TEXT NOT NULL,
                    file_unique_id TEXT PRIMARY KEY,
                    emoji TEXT,
                    file_path TEXT NOT NULL,
                    FOREIGN KEY (pack_name) REFERENCES sticker_packs(name) ON DELETE CASCADE
                )
            """)
            # Custom packs table
            _ = conn.execute("""
                CREATE TABLE IF NOT EXISTS custom_packs (
                    name TEXT PRIMARY KEY,
                    title TEXT NOT NULL
                )
            """)
            # Custom pack stickers table
            _ = conn.execute("""
                CREATE TABLE IF NOT EXISTS custom_pack_stickers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    custom_pack_name TEXT NOT NULL,
                    pack_name TEXT NOT NULL,
                    file_unique_id TEXT NOT NULL,
                    display_order INTEGER NOT NULL,
                    FOREIGN KEY (custom_pack_name) REFERENCES custom_packs(name) ON DELETE CASCADE,
                    FOREIGN KEY (file_unique_id) REFERENCES stickers(file_unique_id) ON DELETE CASCADE
                )
            """)
            # Create indices for better search performance
            _ = conn.execute("CREATE INDEX IF NOT EXISTS idx_stickers_pack ON stickers(pack_name)")
            _ = conn.execute("CREATE INDEX IF NOT EXISTS idx_stickers_emoji ON stickers(emoji)")
            _ = conn.execute("CREATE INDEX IF NOT EXISTS idx_custom_pack_stickers_pack ON custom_pack_stickers(custom_pack_name)")
            conn.commit()

    # Sticker Pack Operations
    def upsert_sticker_pack(self, pack: StickerPackRecord) -> None:
        with self._connect() as conn:
            _ = conn.execute("""
                INSERT INTO sticker_packs (name, title, artist, last_update, sticker_count)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    title = excluded.title,
                    artist = excluded.artist,
                    last_update = excluded.last_update,
                    sticker_count = excluded.sticker_count
            """, (pack['name'], pack['title'], pack['artist'], pack['last_update'], pack['sticker_count']))
            conn.commit()

    def get_sticker_pack(self, pack_name: str) -> StickerPackRecord | None:
        with self._connect() as conn:
            cursor: sqlite3.Cursor = conn.execute(
                "SELECT name, title, artist, last_update, sticker_count FROM sticker_packs WHERE name = ?",
                (pack_name,)
            )
            row = cursor.fetchone()
            if row:
                return StickerPackRecord(
                    name=row['name'],
                    title=row['title'],
                    artist=row['artist'],
                    last_update=row['last_update'],
                    sticker_count=row['sticker_count']
                )
            return None

    def search_sticker_packs(self, query: str) -> list[StickerPackRecord]:
        with self._connect() as conn:
            if not query:
                cursor: sqlite3.Cursor = conn.execute(
                    "SELECT name, title, artist, last_update, sticker_count FROM sticker_packs ORDER BY last_update DESC"
                )
            else:
                query_pattern: str = f"%{query}%"
                cursor = conn.execute("""
                    SELECT name, title, artist, last_update, sticker_count 
                    FROM sticker_packs
                    WHERE name LIKE ? COLLATE NOCASE 
                       OR title LIKE ? COLLATE NOCASE 
                       OR artist LIKE ? COLLATE NOCASE
                    ORDER BY last_update DESC
                """, (query_pattern, query_pattern, query_pattern))
            return [
                StickerPackRecord(
                    name=row['name'],
                    title=row['title'],
                    artist=row['artist'],
                    last_update=row['last_update'],
                    sticker_count=row['sticker_count']
                )
                for row in cursor.fetchall()
            ]

    def update_pack_artist(self, pack_name: str, artist: str) -> bool:
        with self._connect() as conn:
            cursor: sqlite3.Cursor = conn.execute(
                "UPDATE sticker_packs SET artist = ? WHERE name = ?",
                (artist, pack_name)
            )
            conn.commit()
            return cursor.rowcount > 0

    # Sticker Operations
    def upsert_sticker(self, pack_name: str, sticker: StickerRecord) -> None:
        with self._connect() as conn:
            _ = conn.execute("""
                INSERT INTO stickers (pack_name, file_id, file_unique_id, emoji, file_path)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(file_unique_id) DO UPDATE SET
                    file_id = excluded.file_id,
                    emoji = excluded.emoji,
                    file_path = excluded.file_path
            """, (
                pack_name,
                sticker['file_id'],
                sticker['file_unique_id'],
                sticker['emoji'],
                sticker['file_path']
            ))
            conn.commit()

    def get_pack_stickers(self, pack_name: str) -> list[StickerRecord]:
        with self._connect() as conn:
            cursor: sqlite3.Cursor = conn.execute("""
                SELECT file_id, file_unique_id, emoji, file_path
                FROM stickers
                WHERE pack_name = ?
                ORDER BY file_unique_id
            """, (pack_name,))
            return [
                StickerRecord(
                    file_id=row['file_id'],
                    file_unique_id=row['file_unique_id'],
                    emoji=row['emoji'],
                    file_path=row['file_path']
                )
                for row in cursor.fetchall()
            ]

    def get_sticker_unique_ids(self, pack_name: str) -> set[str]:
        with self._connect() as conn:
            cursor: sqlite3.Cursor = conn.execute(
                "SELECT file_unique_id FROM stickers WHERE pack_name = ?",
                (pack_name,)
            )
            return {row['file_unique_id'] for row in cursor.fetchall()}

    def update_sticker_emoji(self, pack_name: str, file_unique_id: str, emoji: str) -> bool:
        with self._connect() as conn:
            cursor: sqlite3.Cursor = conn.execute("""
                UPDATE stickers
                SET emoji = ?
                WHERE pack_name = ? AND file_unique_id = ?
            """, (emoji, pack_name, file_unique_id))
            conn.commit()
            return cursor.rowcount > 0

    def search_stickers(self, query: str) -> list[StickerSearchResult]:
        with self._connect() as conn:
            if not query:
                cursor: sqlite3.Cursor = conn.execute("""
                    SELECT s.pack_name, p.title, p.artist, s.file_unique_id, s.emoji, s.file_path
                    FROM stickers s
                    JOIN sticker_packs p ON s.pack_name = p.name
                    ORDER BY p.last_update DESC
                    LIMIT 100
                """)
            else:
                query_pattern: str = f"%{query}%"
                cursor = conn.execute("""
                    SELECT s.pack_name, p.title, p.artist, s.file_unique_id, s.emoji, s.file_path
                    FROM stickers s
                    JOIN sticker_packs p ON s.pack_name = p.name
                    WHERE s.pack_name LIKE ? COLLATE NOCASE
                       OR p.title LIKE ? COLLATE NOCASE
                       OR p.artist LIKE ? COLLATE NOCASE
                       OR s.emoji LIKE ? COLLATE NOCASE
                    ORDER BY p.last_update DESC
                    LIMIT 200
                """, (query_pattern, query_pattern, query_pattern, query_pattern))
            return [
                StickerSearchResult(
                    pack_name=row['pack_name'],
                    pack_title=row['title'],
                    artist=row['artist'],
                    file_unique_id=row['file_unique_id'],
                    emoji=row['emoji'] or "",
                    file_path=row['file_path']
                )
                for row in cursor.fetchall()
            ]

    # Custom Pack Operations
    def create_custom_pack(self, name: str, title: str) -> bool:
        try:
            with self._connect() as conn:
                _ = conn.execute(
                    "INSERT INTO custom_packs (name, title) VALUES (?, ?)",
                    (name, title)
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def get_custom_pack(self, name: str) -> CustomPackRecord | None:
        with self._connect() as conn:
            cursor: sqlite3.Cursor = conn.execute(
                "SELECT name, title FROM custom_packs WHERE name = ?",
                (name,)
            )
            row = cursor.fetchone()
            if row:
                return CustomPackRecord(name=row['name'], title=row['title'])
            return None

    def get_all_custom_packs(self) -> list[tuple[CustomPackRecord, int]]:
        with self._connect() as conn:
            cursor: sqlite3.Cursor = conn.execute("""
                SELECT cp.name, cp.title, COUNT(cps.id) as sticker_count
                FROM custom_packs cp
                LEFT JOIN custom_pack_stickers cps ON cp.name = cps.custom_pack_name
                GROUP BY cp.name, cp.title
                ORDER BY cp.name
            """)
            return [
                (CustomPackRecord(name=row['name'], title=row['title']), row['sticker_count'])
                for row in cursor.fetchall()
            ]

    def update_custom_pack(self, name: str, title: str, stickers: list[CustomPackSticker]) -> bool:
        try:
            with self._connect() as conn:
                # Update title
                _ = conn.execute("UPDATE custom_packs SET title = ? WHERE name = ?", (title, name))
                # Delete existing stickers
                _ = conn.execute("DELETE FROM custom_pack_stickers WHERE custom_pack_name = ?", (name,))
                # Insert new stickers
                for idx, sticker in enumerate(stickers):
                    _ = conn.execute("""
                        INSERT INTO custom_pack_stickers 
                        (custom_pack_name, pack_name, file_unique_id, display_order)
                        VALUES (?, ?, ?, ?)
                    """, (name, sticker['pack_name'], sticker['file_unique_id'], idx))
                conn.commit()
                return True
        except Exception:
            return False

    def delete_custom_pack(self, name: str) -> bool:
        try:
            with self._connect() as conn:
                cursor: sqlite3.Cursor = conn.execute("DELETE FROM custom_packs WHERE name = ?", (name,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception:
            return False

    def get_custom_pack_stickers(self, pack_name: str) -> list[CustomPackSticker]:
        with self._connect() as conn:
            cursor: sqlite3.Cursor = conn.execute("""
                SELECT cps.pack_name, p.title, s.file_unique_id, s.file_path, s.emoji
                FROM custom_pack_stickers cps
                JOIN stickers s ON cps.file_unique_id = s.file_unique_id
                JOIN sticker_packs p ON cps.pack_name = p.name
                WHERE cps.custom_pack_name = ?
                ORDER BY cps.display_order
            """, (pack_name,))
            return [
                CustomPackSticker(
                    pack_name=row['pack_name'],
                    pack_title=row['title'],
                    file_unique_id=row['file_unique_id'],
                    file_path=row['file_path'],
                    emoji=row['emoji'] or ""
                )
                for row in cursor.fetchall()
            ]

    # Export Operations
    def export_sticker_packs_to_json(self) -> str:
        with self._connect() as conn:
            cursor: sqlite3.Cursor = conn.execute("""
                SELECT name, title, artist, last_update, sticker_count
                FROM sticker_packs
                ORDER BY name
            """)
            packs_dict: dict[str, dict[str, str | int]] = {
                row['name']: {
                    'name': row['name'],
                    'title': row['title'],
                    'artist': row['artist'],
                    'last_update': row['last_update'],
                    'sticker_count': row['sticker_count']
                }
                for row in cursor.fetchall()
            }
            return json.dumps(packs_dict, ensure_ascii=False, indent=2)

    def export_stickers_to_json(self, pack_name: str) -> str:
        stickers: list[StickerRecord] = self.get_pack_stickers(pack_name)
        stickers_dict: dict[str, dict[str, str | None]] = {
            sticker['file_unique_id']: dict(sticker)
            for sticker in stickers
        }
        return json.dumps(stickers_dict, ensure_ascii=False, indent=2)

    def export_custom_packs_to_json(self) -> str:
        with self._connect() as conn:
            cursor: sqlite3.Cursor = conn.execute("SELECT name, title FROM custom_packs")
            packs = cursor.fetchall()
            result: dict[str, dict[str, str | list[dict[str, str]]]] = {}
            for row in packs:
                pack_name: str = row['name']
                pack_title: str = row['title']
                stickers: list[CustomPackSticker] = self.get_custom_pack_stickers(pack_name)
                result[pack_name] = {
                    'name': pack_name,
                    'title': pack_title,
                    'stickers': [dict(s) for s in stickers]
                }
            return json.dumps(result, ensure_ascii=False, indent=2)
