from __future__ import annotations

import sqlite3
from pathlib import Path

from app.config import DATA_DIR, DB_PATH, UPLOAD_DIR
from app.db.schema import SCHEMA_SQL, SEED_CATEGORIES


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path | None = None) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        for name in SEED_CATEGORIES:
            conn.execute(
                "INSERT OR IGNORE INTO categories(name) VALUES (?)",
                (name,),
            )
        conn.commit()
    finally:
        conn.close()
