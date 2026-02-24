import sqlite3
from pathlib import Path

DB_NAME = "tenders.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS raw_tenders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tender_id TEXT UNIQUE,
        title TEXT,
        description TEXT,
        customer TEXT,
        price REAL,
        publish_date TEXT,
        source_url TEXT,
        raw_json TEXT,
        parsed_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS classified_tenders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tender_id TEXT UNIQUE,
        category TEXT,
        confidence REAL,
        classified_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Индексы для скорости
    cur.execute("CREATE INDEX IF NOT EXISTS idx_raw_tender_id ON raw_tenders(tender_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_classified_tender_id ON classified_tenders(tender_id);")

    conn.commit()
    conn.close()