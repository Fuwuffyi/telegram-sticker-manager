import json
from pathlib import Path
from typing import TypedDict

import duckdb

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

    def _init_database(self) -> None:
        with duckdb.connect(str(self.db_path)) as conn:
            # Sticker packs table
            _ = conn.execute("""
                CREATE TABLE IF NOT EXISTS sticker_packs (
                    name VARCHAR PRIMARY KEY,
                    title VARCHAR NOT NULL,
                    artist VARCHAR NOT NULL,
                    last_update BIGINT NOT NULL,
                    sticker_count INTEGER NOT NULL
                )
            """)
            # Stickers table
            _ = conn.execute("""
                CREATE TABLE IF NOT EXISTS stickers (
                    pack_name VARCHAR NOT NULL,
                    file_id VARCHAR NOT NULL,
                    file_unique_id VARCHAR PRIMARY KEY,
                    emoji VARCHAR,
                    file_path VARCHAR NOT NULL,
                    FOREIGN KEY (pack_name) REFERENCES sticker_packs(name) ON DELETE CASCADE
                )
            """)
            # Custom packs table
            _ = conn.execute("""
                CREATE TABLE IF NOT EXISTS custom_packs (
                    name VARCHAR PRIMARY KEY,
                    title VARCHAR NOT NULL
                )
            """)
            # Custom pack stickers table
            _ = conn.execute("""
                CREATE TABLE IF NOT EXISTS custom_pack_stickers (
                    id INTEGER PRIMARY KEY,
                    custom_pack_name VARCHAR NOT NULL,
                    pack_name VARCHAR NOT NULL,
                    file_unique_id VARCHAR NOT NULL,
                    display_order INTEGER NOT NULL,
                    FOREIGN KEY (custom_pack_name) REFERENCES custom_packs(name) ON DELETE CASCADE,
                    FOREIGN KEY (file_unique_id) REFERENCES stickers(file_unique_id) ON DELETE CASCADE
                )
            """)
            # Create indexes for better search performance
            _ = conn.execute("CREATE INDEX IF NOT EXISTS idx_stickers_pack ON stickers(pack_name)")
            _ = conn.execute("CREATE INDEX IF NOT EXISTS idx_stickers_emoji ON stickers(emoji)")
            _ = conn.execute("CREATE INDEX IF NOT EXISTS idx_custom_pack_stickers_pack ON custom_pack_stickers(custom_pack_name)")

    # Sticker Pack Operations
    def upsert_sticker_pack(self, pack: StickerPackRecord) -> None:
        with duckdb.connect(str(self.db_path)) as conn:
            _ = conn.execute("""
                INSERT INTO sticker_packs (name, title, artist, last_update, sticker_count)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (name) DO UPDATE SET
                    title = EXCLUDED.title,
                    artist = EXCLUDED.artist,
                    last_update = EXCLUDED.last_update,
                    sticker_count = EXCLUDED.sticker_count
            """, [pack['name'], pack['title'], pack['artist'], pack['last_update'], pack['sticker_count']])

    def get_sticker_pack(self, pack_name: str) -> StickerPackRecord | None:
        with duckdb.connect(str(self.db_path)) as conn:
            result = conn.execute(
                "SELECT name, title, artist, last_update, sticker_count FROM sticker_packs WHERE name = ?",
                [pack_name]
            ).fetchone()
            if result:
                return StickerPackRecord(
                    name=result[0],
                    title=result[1],
                    artist=result[2],
                    last_update=result[3],
                    sticker_count=result[4]
                )
            return None

    def search_sticker_packs(self, query: str) -> list[StickerPackRecord]:
        with duckdb.connect(str(self.db_path)) as conn:
            if not query:
                results = conn.execute(
                    "SELECT name, title, artist, last_update, sticker_count FROM sticker_packs ORDER BY last_update DESC"
                ).fetchall()
            else:
                query_pattern = f"%{query}%"
                results = conn.execute("""
                    SELECT name, title, artist, last_update, sticker_count 
                    FROM sticker_packs 
                    WHERE name ILIKE ? OR title ILIKE ? OR artist ILIKE ?
                    ORDER BY last_update DESC
                """, [query_pattern, query_pattern, query_pattern]).fetchall()
            return [
                StickerPackRecord(
                    name=row[0],
                    title=row[1],
                    artist=row[2],
                    last_update=row[3],
                    sticker_count=row[4]
                )
                for row in results
            ]

    def update_pack_artist(self, pack_name: str, artist: str) -> bool:
        with duckdb.connect(str(self.db_path)) as conn:
            conn.execute(
                "UPDATE sticker_packs SET artist = ? WHERE name = ?",
                [artist, pack_name]
            )
            return conn.execute("SELECT changes()").fetchone()[0] > 0

    # Sticker Operations
    def upsert_sticker(self, pack_name: str, sticker: StickerRecord) -> None:
        with duckdb.connect(str(self.db_path)) as conn:
            _ = conn.execute("""
                INSERT INTO stickers (pack_name, file_id, file_unique_id, emoji, file_path)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (file_unique_id) DO UPDATE SET
                    file_id = EXCLUDED.file_id,
                    emoji = EXCLUDED.emoji,
                    file_path = EXCLUDED.file_path
            """, [
                pack_name,
                sticker['file_id'],
                sticker['file_unique_id'],
                sticker['emoji'],
                sticker['file_path']
            ])

    def get_pack_stickers(self, pack_name: str) -> list[StickerRecord]:
        with duckdb.connect(str(self.db_path)) as conn:
            results = conn.execute("""
                SELECT file_id, file_unique_id, emoji, file_path
                FROM stickers
                WHERE pack_name = ?
                ORDER BY file_unique_id
            """, [pack_name]).fetchall()
            return [
                StickerRecord(
                    file_id=row[0],
                    file_unique_id=row[1],
                    emoji=row[2],
                    file_path=row[7]
                )
                for row in results
            ]

    def get_sticker_unique_ids(self, pack_name: str) -> set[str]:
        with duckdb.connect(str(self.db_path)) as conn:
            results = conn.execute(
                "SELECT file_unique_id FROM stickers WHERE pack_name = ?",
                [pack_name]
            ).fetchall()
            return {row[0] for row in results}

    def update_sticker_emoji(self, pack_name: str, file_unique_id: str, emoji: str) -> bool:
        with duckdb.connect(str(self.db_path)) as conn:
            conn.execute("""
                UPDATE stickers 
                SET emoji = ? 
                WHERE pack_name = ? AND file_unique_id = ?
            """, [emoji, pack_name, file_unique_id])
            return conn.execute("SELECT changes()").fetchone()[0] > 0

    def search_stickers(self, query: str) -> list[StickerSearchResult]:
        with duckdb.connect(str(self.db_path)) as conn:
            if not query:
                results = conn.execute("""
                    SELECT s.pack_name, p.title, p.artist, s.file_unique_id, s.emoji,
                           s.file_path
                    FROM stickers s
                    JOIN sticker_packs p ON s.pack_name = p.name
                    ORDER BY p.last_update DESC
                    LIMIT 100
                """).fetchall()
            else:
                query_pattern = f"%{query}%"
                results = conn.execute("""
                    SELECT s.pack_name, p.title, p.artist, s.file_unique_id, s.emoji,
                           s.file_path
                    FROM stickers s
                    JOIN sticker_packs p ON s.pack_name = p.name
                    WHERE s.pack_name ILIKE ? 
                       OR p.title ILIKE ? 
                       OR p.artist ILIKE ? 
                       OR s.emoji ILIKE ?
                    ORDER BY p.last_update DESC
                    LIMIT 200
                """, [query_pattern, query_pattern, query_pattern, query_pattern]).fetchall()
            return [
                StickerSearchResult(
                    pack_name=row[0],
                    pack_title=row[1],
                    artist=row[2],
                    file_unique_id=row[3],
                    emoji=row[4] or "",
                    file_path=row[5]
                )
                for row in results
            ]

    # Custom Pack Operations
    def create_custom_pack(self, name: str, title: str) -> bool:
        try:
            with duckdb.connect(str(self.db_path)) as conn:
                conn.execute(
                    "INSERT INTO custom_packs (name, title) VALUES (?, ?)",
                    [name, title]
                )
                return True
        except duckdb.ConstraintException:
            return False

    def get_custom_pack(self, name: str) -> CustomPackRecord | None:
        with duckdb.connect(str(self.db_path)) as conn:
            result = conn.execute(
                "SELECT name, title FROM custom_packs WHERE name = ?",
                [name]
            ).fetchone()
            if result:
                return CustomPackRecord(name=result[0], title=result[1])
            return None

    def get_all_custom_packs(self) -> list[tuple[CustomPackRecord, int]]:
        with duckdb.connect(str(self.db_path)) as conn:
            results = conn.execute("""
                SELECT cp.name, cp.title, COUNT(cps.id) as sticker_count
                FROM custom_packs cp
                LEFT JOIN custom_pack_stickers cps ON cp.name = cps.custom_pack_name
                GROUP BY cp.name, cp.title
                ORDER BY cp.name
            """).fetchall()
            return [
                (CustomPackRecord(name=row[0], title=row[1]), row[2])
                for row in results
            ]

    def update_custom_pack(self, name: str, title: str, stickers: list[CustomPackSticker]) -> bool:
        try:
            with duckdb.connect(str(self.db_path)) as conn:
                # Update title
                _ = conn.execute("UPDATE custom_packs SET title = ? WHERE name = ?", [title, name])
                # Delete existing stickers
                _ = conn.execute("DELETE FROM custom_pack_stickers WHERE custom_pack_name = ?", [name])
                # Insert new stickers
                for idx, sticker in enumerate(stickers):
                    conn.execute("""
                        INSERT INTO custom_pack_stickers 
                        (custom_pack_name, pack_name, file_unique_id, display_order)
                        VALUES (?, ?, ?, ?)
                    """, [name, sticker['pack_name'], sticker['file_unique_id'], idx])
                return True
        except Exception:
            return False

    def delete_custom_pack(self, name: str) -> bool:
        with duckdb.connect(str(self.db_path)) as conn:
            _ = conn.execute("DELETE FROM custom_packs WHERE name = ?", [name])
            return conn.execute("SELECT changes()").fetchone()[0] > 0

    def get_custom_pack_stickers(self, pack_name: str) -> list[CustomPackSticker]:
        with duckdb.connect(str(self.db_path)) as conn:
            results = conn.execute("""
                SELECT cps.pack_name, p.title, s.file_unique_id, s.file_path, s.emoji
                FROM custom_pack_stickers cps
                JOIN stickers s ON cps.file_unique_id = s.file_unique_id
                JOIN sticker_packs p ON cps.pack_name = p.name
                WHERE cps.custom_pack_name = ?
                ORDER BY cps.display_order
            """, [pack_name]).fetchall()
            return [
                CustomPackSticker(
                    pack_name=row[0],
                    pack_title=row[1],
                    file_unique_id=row[2],
                    file_path=row[3],
                    emoji=row[4] or ""
                )
                for row in results
            ]

    # Export Operations
    def export_sticker_packs_to_json(self) -> str:
        with duckdb.connect(str(self.db_path)) as conn:
            packs = conn.execute("""
                SELECT name, title, artist, last_update, sticker_count
                FROM sticker_packs
                ORDER BY name
            """).fetchall()
            packs_dict = {
                row[0]: {
                    'name': row[0],
                    'title': row[1],
                    'artist': row[2],
                    'last_update': row[3],
                    'sticker_count': row[4]
                }
                for row in packs
            }
            return json.dumps(packs_dict, ensure_ascii=False, indent=2)

    def export_stickers_to_json(self, pack_name: str) -> str:
        stickers = self.get_pack_stickers(pack_name)
        stickers_dict = {
            sticker['file_unique_id']: dict(sticker)
            for sticker in stickers
        }
        return json.dumps(stickers_dict, ensure_ascii=False, indent=2)

    def export_custom_packs_to_json(self) -> str:
        with duckdb.connect(str(self.db_path)) as conn:
            packs = conn.execute("SELECT name, title FROM custom_packs").fetchall()
            result = {}
            for pack_name, pack_title in packs:
                stickers = self.get_custom_pack_stickers(pack_name)
                result[pack_name] = {
                    'name': pack_name,
                    'title': pack_title,
                    'stickers': [dict(s) for s in stickers]
                }
            return json.dumps(result, ensure_ascii=False, indent=2)
