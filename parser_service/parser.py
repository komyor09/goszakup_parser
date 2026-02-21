import sqlite3
import json
import time
from playwright.sync_api import sync_playwright

DB_NAME = "tenders.db"
TENDERS_LIMIT = 200  #


def init_db():
    conn = sqlite3.connect(DB_NAME)
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
    )
    """)

    conn.commit()
    conn.close()


def save_tender(data):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    try:
        cur.execute("""
        INSERT OR IGNORE INTO raw_tenders
        (tender_id, title, description, customer, price, publish_date, source_url, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("id"),
            data.get("name"),
            data.get("description"),
            data.get("customer"),
            data.get("amount"),
            data.get("publishDate"),
            data.get("url"),
            json.dumps(data, ensure_ascii=False)
        ))
        conn.commit()
    except Exception as e:
        print("DB ERROR:", e)

    conn.close()


def parse_tenders(limit):
    collected = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://goszakup.gov.kz/ru/search/lots")
        page.wait_for_timeout(5000)

        while collected < limit:
            # Получаем HTML
            html = page.content()

            # ИЩЕМ JSON В NETWORK ВРУЧНУЮ
            # (на практике лучше перехватывать response)

            # Заглушка: если данные уже в DOM
            items = page.query_selector_all("div.lot-row")

            for item in items:
                if collected >= limit:
                    break

                title = item.inner_text()

                data = {
                    "id": str(hash(title)),
                    "name": title,
                    "description": "",
                    "customer": "",
                    "amount": 0,
                    "publishDate": "",
                    "url": page.url
                }

                save_tender(data)
                collected += 1

            # Кнопка следующей страницы
            next_btn = page.query_selector("a.next")
            if next_btn:
                next_btn.click()
                page.wait_for_timeout(4000)
            else:
                break

        browser.close()


if __name__ == "__main__":
    init_db()
    parse_tenders(TENDERS_LIMIT)