CREATE TABLE raw_tenders (
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
CREATE TABLE classified_tenders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_id TEXT UNIQUE,
    category TEXT,
    confidence REAL,
    classified_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
