from playwright.sync_api import sync_playwright
from db.database import get_connection
import json

TENDERS_LIMIT = 200

def save_tender(data):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR IGNORE INTO raw_tenders
        (tender_id, title, description, customer, price, publish_date, source_url, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["id"],
        data["title"],
        data["description"],
        data["customer"],
        data["price"],
        data["date"],
        data["url"],
        json.dumps(data, ensure_ascii=False)
    ))

    conn.commit()
    conn.close()