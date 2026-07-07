"""Sidecar edit log database interface."""

import os
import sqlite3
from datetime import datetime

# DB_PATH is configurable to allow tests to override it with ':memory:'
DB_PATH = os.path.join(os.path.dirname(__file__), "db", "edit_log.db")
_conn = None

def get_connection():
    """Gets the shared SQLite connection with check_same_thread=False and WAL mode."""
    global _conn
    if _conn is None:
        if DB_PATH != ":memory:":
            # Ensure the db/ directory exists
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL;")
    return _conn

def close_connection():
    """Closes and resets the shared connection."""
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None

def init_db() -> None:
    """Creates the edit_log table if it doesn't already exist."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS edit_log (
      id            INTEGER PRIMARY KEY AUTOINCREMENT,
      ts            TEXT NOT NULL,
      original_seg  TEXT NOT NULL,
      proposed_seg  TEXT NOT NULL,
      accepted      INTEGER NOT NULL,  -- 0 or 1
      de_ai_level   INTEGER NOT NULL,
      voice_level   INTEGER NOT NULL,
      mode          TEXT NOT NULL,     -- 'my_voice' | 'ceo_archetype'
      model_used    TEXT NOT NULL      -- 'ft' | 'rag_fallback' | 'base_fallback' | 'stub'
    );
    """)
    conn.commit()

def log_edit(original_seg: str, proposed_seg: str, accepted, de_ai_level: int, 
             voice_level: int, mode: str, model_used: str) -> None:
    """Logs a rewrite decision into the database."""
    conn = get_connection()
    cursor = conn.cursor()
    ts = datetime.utcnow().isoformat()
    # Store accepted as 0 or 1
    accepted_val = 1 if accepted else 0
    cursor.execute("""
    INSERT INTO edit_log (ts, original_seg, proposed_seg, accepted, de_ai_level, voice_level, mode, model_used)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, (ts, original_seg, proposed_seg, accepted_val, de_ai_level, voice_level, mode, model_used))
    conn.commit()
