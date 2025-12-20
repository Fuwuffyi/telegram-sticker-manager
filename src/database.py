import json
import time
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
    signal_url: str | None
    signal_uploaded_at: int | None
    used_in_custom_packs: bool

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
    signal_url: str | None
    signal_uploaded_at: int | None
    last_modified: int

class Database:
    def __init__(self, db_path: Path) -> None:
        self.db_path: Path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _connect(self) -> sqlite3.Connection:
        conn: sqlite3.Connection = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
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
                    sticker_count INTEGER NOT NULL,
                    signal_url TEXT,
                    signal_uploaded_at INTEGER
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
                    title TEXT NOT NULL,
                    signal_url TEXT,
                    signal_uploaded_at INTEGER,
                    last_modified INTEGER NOT NULL DEFAULT 0
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
            _ = conn.execute("CREATE INDEX IF NOT EXISTS idx_sticker_packs_last_update ON sticker_packs(last_update DESC)")
            _ = conn.execute("CREATE INDEX IF NOT EXISTS idx_custom_pack_stickers_unique_id ON custom_pack_stickers(file_unique_id)")
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
                """SELECT name, title, artist, last_update, sticker_count, 
                   signal_url, signal_uploaded_at FROM sticker_packs WHERE name = ?""",
                (pack_name,)
            )
            row = cursor.fetchone()
            if row:
                # Check if pack is used in custom packs
                used_cursor: sqlite3.Cursor = conn.execute("""
                    SELECT COUNT(DISTINCT custom_pack_name) FROM custom_pack_stickers
                    JOIN stickers ON custom_pack_stickers.file_unique_id = stickers.file_unique_id
                    WHERE stickers.pack_name = ?
                """, (pack_name,))
                used_in_custom: bool = used_cursor.fetchone()[0] > 0
                return StickerPackRecord(
                    name=row['name'],
                    title=row['title'],
                    artist=row['artist'],
                    last_update=row['last_update'],
                    sticker_count=row['sticker_count'],
                    signal_url=row['signal_url'],
                    signal_uploaded_at=row['signal_uploaded_at'],
                    used_in_custom_packs=used_in_custom
                )
            return None

    def search_sticker_packs(self, query: str, page: int = 1, per_page: int = 50) -> tuple[list[StickerPackRecord], int]:
        with self._connect() as conn:
            offset: int = (page - 1) * per_page
            if not query:
                # Get total count
                cursor: sqlite3.Cursor = conn.execute("SELECT COUNT(*) FROM sticker_packs")
                total: int = cursor.fetchone()[0]
                # Get paginated results
                cursor: sqlite3.Cursor = conn.execute("""
                    SELECT name, title, artist, last_update, sticker_count,
                           signal_url, signal_uploaded_at
                    FROM sticker_packs 
                    ORDER BY last_update DESC
                    LIMIT ? OFFSET ?
                """, (per_page, offset))
            else:
                query_pattern: str = f"%{query}%"
                # Get total count
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM sticker_packs
                    WHERE name LIKE ? COLLATE NOCASE
                       OR title LIKE ? COLLATE NOCASE
                       OR artist LIKE ? COLLATE NOCASE
                """, (query_pattern, query_pattern, query_pattern))
                total = cursor.fetchone()[0]
                # Get paginated results
                cursor = conn.execute("""
                    SELECT name, title, artist, last_update, sticker_count,
                           signal_url, signal_uploaded_at
                    FROM sticker_packs
                    WHERE name LIKE ? COLLATE NOCASE
                       OR title LIKE ? COLLATE NOCASE
                       OR artist LIKE ? COLLATE NOCASE
                    ORDER BY last_update DESC
                    LIMIT ? OFFSET ?
                """, (query_pattern, query_pattern, query_pattern, per_page, offset))
            packs = []
            for row in cursor.fetchall():
                # Check if pack is used in custom packs
                used_cursor = conn.execute("""
                    SELECT COUNT(DISTINCT custom_pack_name) FROM custom_pack_stickers
                    JOIN stickers ON custom_pack_stickers.file_unique_id = stickers.file_unique_id
                    WHERE stickers.pack_name = ?
                """, (row['name'],))
                used_in_custom: bool = used_cursor.fetchone()[0] > 0
                packs.append(StickerPackRecord(
                    name=row['name'],
                    title=row['title'],
                    artist=row['artist'],
                    last_update=row['last_update'],
                    sticker_count=row['sticker_count'],
                    signal_url=row['signal_url'],
                    signal_uploaded_at=row['signal_uploaded_at'],
                    used_in_custom_packs=used_in_custom
                ))
            return packs, total

    def update_pack_signal_url(self, pack_name: str, signal_url: str, uploaded_at: int) -> bool:
        with self._connect() as conn:
            cursor: sqlite3.Cursor = conn.execute(
                "UPDATE sticker_packs SET signal_url = ?, signal_uploaded_at = ? WHERE name = ?",
                (signal_url, uploaded_at, pack_name)
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_pack_thumbnail_stickers(self, pack_name: str, limit: int = 4) -> list[StickerRecord]:
        with self._connect() as conn:
            cursor: sqlite3.Cursor = conn.execute("""
                SELECT file_id, file_unique_id, emoji, file_path
                FROM stickers
                WHERE pack_name = ?
                ORDER BY file_unique_id
                LIMIT ?
            """, (pack_name, limit))
            return [
                StickerRecord(
                    file_id=row['file_id'],
                    file_unique_id=row['file_unique_id'],
                    emoji=row['emoji'],
                    file_path=row['file_path']
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

    def delete_sticker_pack(self, pack_name: str) -> bool:
        try:
            with self._connect() as conn:
                cursor: sqlite3.Cursor = conn.execute("DELETE FROM sticker_packs WHERE name = ?", (pack_name,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception:
            return False

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

    def get_pack_stickers(self, pack_name: str, page: int = 1, per_page: int = 100) -> tuple[list[StickerRecord], int]:
        with self._connect() as conn:
            offset: int = (page - 1) * per_page
            # Get total count
            cursor: sqlite3.Cursor = conn.execute(
                "SELECT COUNT(*) FROM stickers WHERE pack_name = ?",
                (pack_name,)
            )
            total: int = cursor.fetchone()[0]
            # Get paginated results
            cursor = conn.execute("""
                SELECT file_id, file_unique_id, emoji, file_path
                FROM stickers
                WHERE pack_name = ?
                ORDER BY file_unique_id
                LIMIT ? OFFSET ?
            """, (pack_name, per_page, offset))
            stickers = [
                StickerRecord(
                    file_id=row['file_id'],
                    file_unique_id=row['file_unique_id'],
                    emoji=row['emoji'],
                    file_path=row['file_path']
                )
                for row in cursor.fetchall()
            ]
            return stickers, total

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

    def search_stickers(self, query: str, page: int = 1, per_page: int = 100) -> tuple[list[StickerSearchResult], int]:
        with self._connect() as conn:
            offset: int = (page - 1) * per_page
            if not query:
                # Get total count
                cursor: sqlite3.Cursor = conn.execute("""
                    SELECT COUNT(*) FROM stickers s
                    JOIN sticker_packs p ON s.pack_name = p.name
                """)
                total: int = cursor.fetchone()[0]
                # Get paginated results
                cursor = conn.execute("""
                    SELECT s.pack_name, p.title, p.artist, s.file_unique_id, s.emoji, s.file_path
                    FROM stickers s
                    JOIN sticker_packs p ON s.pack_name = p.name
                    ORDER BY p.last_update DESC
                    LIMIT ? OFFSET ?
                """, (per_page, offset))
            else:
                query_pattern: str = f"%{query}%"
                # Get total count
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM stickers s
                    JOIN sticker_packs p ON s.pack_name = p.name
                    WHERE s.pack_name LIKE ? COLLATE NOCASE
                       OR p.title LIKE ? COLLATE NOCASE
                       OR p.artist LIKE ? COLLATE NOCASE
                       OR s.emoji LIKE ? COLLATE NOCASE
                """, (query_pattern, query_pattern, query_pattern, query_pattern))
                total = cursor.fetchone()[0]
                # Get paginated results
                cursor = conn.execute("""
                    SELECT s.pack_name, p.title, p.artist, s.file_unique_id, s.emoji, s.file_path
                    FROM stickers s
                    JOIN sticker_packs p ON s.pack_name = p.name
                    WHERE s.pack_name LIKE ? COLLATE NOCASE
                       OR p.title LIKE ? COLLATE NOCASE
                       OR p.artist LIKE ? COLLATE NOCASE
                       OR s.emoji LIKE ? COLLATE NOCASE
                    ORDER BY p.last_update DESC
                    LIMIT ? OFFSET ?
                """, (query_pattern, query_pattern, query_pattern, query_pattern, per_page, offset))
            stickers = [
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
            return stickers, total

    # Custom Pack Operations
    def create_custom_pack(self, name: str, title: str) -> bool:
        try:
            with self._connect() as conn:
                _ = conn.execute(
                    "INSERT INTO custom_packs (name, title, last_modified) VALUES (?, ?, ?)",
                    (name, title, int(time.time()))
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def get_custom_pack(self, name: str) -> CustomPackRecord | None:
        with self._connect() as conn:
            cursor: sqlite3.Cursor = conn.execute(
                """SELECT name, title, signal_url, signal_uploaded_at, last_modified 
                   FROM custom_packs WHERE name = ?""",
                (name,)
            )
            row = cursor.fetchone()
            if row:
                return CustomPackRecord(
                    name=row['name'],
                    title=row['title'],
                    signal_url=row['signal_url'],
                    signal_uploaded_at=row['signal_uploaded_at'],
                    last_modified=row['last_modified']
                )
            return None

    def get_all_custom_packs(self, page: int = 1, per_page: int = 50) -> tuple[list[tuple[CustomPackRecord, int]], int]:
        with self._connect() as conn:
            offset: int = (page - 1) * per_page
            # Get total count
            cursor: sqlite3.Cursor = conn.execute("SELECT COUNT(*) FROM custom_packs")
            total: int = cursor.fetchone()[0]
            # Get paginated results
            cursor = conn.execute("""
                SELECT cp.name, cp.title, cp.signal_url, cp.signal_uploaded_at, 
                       cp.last_modified, COUNT(cps.id) as sticker_count
                FROM custom_packs cp
                LEFT JOIN custom_pack_stickers cps ON cp.name = cps.custom_pack_name
                GROUP BY cp.name, cp.title, cp.signal_url, cp.signal_uploaded_at, cp.last_modified
                ORDER BY cp.name
                LIMIT ? OFFSET ?
            """, (per_page, offset))
            packs = [
                (CustomPackRecord(
                    name=row['name'],
                    title=row['title'],
                    signal_url=row['signal_url'],
                    signal_uploaded_at=row['signal_uploaded_at'],
                    last_modified=row['last_modified']
                ), row['sticker_count'])
                for row in cursor.fetchall()
            ]
            return packs, total

    def update_custom_pack(self, name: str, title: str, stickers: list[CustomPackSticker]) -> bool:
        try:
            with self._connect() as conn:
                # Update title and last_modified
                _ = conn.execute(
                    "UPDATE custom_packs SET title = ?, last_modified = ? WHERE name = ?",
                    (title, int(time.time()), name)
                )
                # Delete existing stickers
                _ = conn.execute("DELETE FROM custom_pack_stickers WHERE custom_pack_name = ?", (name,))
                # Insert new stickers in batch
                if stickers:
                    _ = conn.executemany("""
                        INSERT INTO custom_pack_stickers 
                        (custom_pack_name, pack_name, file_unique_id, display_order)
                        VALUES (?, ?, ?, ?)
                    """, [(name, s['pack_name'], s['file_unique_id'], idx) for idx, s in enumerate(stickers)])
                conn.commit()
                return True
        except Exception:
            return False

    def update_custom_pack_signal_url(self, pack_name: str, signal_url: str, uploaded_at: int) -> bool:
        with self._connect() as conn:
            cursor: sqlite3.Cursor = conn.execute(
                "UPDATE custom_packs SET signal_url = ?, signal_uploaded_at = ? WHERE name = ?",
                (signal_url, uploaded_at, pack_name)
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_custom_pack(self, name: str) -> bool:
        try:
            with self._connect() as conn:
                cursor: sqlite3.Cursor = conn.execute("DELETE FROM custom_packs WHERE name = ?", (name,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception:
            return False

    def get_custom_pack_stickers(self, pack_name: str, page: int = 1, per_page: int = 100) -> tuple[list[CustomPackSticker], int]:
        with self._connect() as conn:
            offset: int = (page - 1) * per_page
            # Get total count
            cursor: sqlite3.Cursor = conn.execute("""
                SELECT COUNT(*) FROM custom_pack_stickers
                WHERE custom_pack_name = ?
            """, (pack_name,))
            total: int = cursor.fetchone()[0]
            # Get paginated results
            cursor = conn.execute("""
                SELECT cps.pack_name, p.title, s.file_unique_id, s.file_path, s.emoji
                FROM custom_pack_stickers cps
                JOIN stickers s ON cps.file_unique_id = s.file_unique_id
                JOIN sticker_packs p ON cps.pack_name = p.name
                WHERE cps.custom_pack_name = ?
                ORDER BY cps.display_order
                LIMIT ? OFFSET ?
            """, (pack_name, per_page, offset))
            stickers = [
                CustomPackSticker(
                    pack_name=row['pack_name'],
                    pack_title=row['title'],
                    file_unique_id=row['file_unique_id'],
                    file_path=row['file_path'],
                    emoji=row['emoji'] or ""
                )
                for row in cursor.fetchall()
            ]
            return stickers, total

    # Export Operations
    def export_sticker_packs_to_json(self) -> str:
        with self._connect() as conn:
            cursor: sqlite3.Cursor = conn.execute("""
                SELECT name, title, artist, last_update, sticker_count,
                       signal_url, signal_uploaded_at
                FROM sticker_packs
                ORDER BY name
            """)
            packs_dict: dict[str, dict[str, str | int | None]] = {
                row['name']: {
                    'name': row['name'],
                    'title': row['title'],
                    'artist': row['artist'],
                    'last_update': row['last_update'],
                    'sticker_count': row['sticker_count'],
                    'signal_url': row['signal_url'],
                    'signal_uploaded_at': row['signal_uploaded_at']
                }
                for row in cursor.fetchall()
            }
            return json.dumps(packs_dict, ensure_ascii=False, indent=2)

    def export_stickers_to_json(self, pack_name: str) -> str:
        stickers, _ = self.get_pack_stickers(pack_name, page=1, per_page=10000)
        stickers_dict: dict[str, dict[str, str | None]] = {
            sticker['file_unique_id']: dict(sticker)
            for sticker in stickers
        }
        return json.dumps(stickers_dict, ensure_ascii=False, indent=2)

    def export_custom_packs_to_json(self) -> str:
        with self._connect() as conn:
            cursor: sqlite3.Cursor = conn.execute(
                "SELECT name, title, signal_url, signal_uploaded_at, last_modified FROM custom_packs"
            )
            packs = cursor.fetchall()
            result: dict[str, dict[str, str | int | None | list[dict[str, str]]]] = {}
            for row in packs:
                pack_name: str = row['name']
                pack_title: str = row['title']
                stickers, _ = self.get_custom_pack_stickers(pack_name, page=1, per_page=10000)
                result[pack_name] = {
                    'name': pack_name,
                    'title': pack_title,
                    'signal_url': row['signal_url'],
                    'signal_uploaded_at': row['signal_uploaded_at'],
                    'last_modified': row['last_modified'],
                    'stickers': [dict(s) for s in stickers]
                }
            return json.dumps(result, ensure_ascii=False, indent=2)
