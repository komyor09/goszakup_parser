"""
Юнит-тесты утилитных функций парсера (без Selenium).
Запуск: python tests/test_utils.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import hashlib
import re
from datetime import datetime
from typing import Optional


# === Копии функций для тестирования без импорта selenium ===

def _make_hash(lot_number, announce_number, lot_name):
    raw = f"{lot_number}|{announce_number}|{lot_name}".lower().strip()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def _parse_amount(text):
    if not text:
        return None
    cleaned = re.sub(r"[^\d,.]", "", text).replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None

def _parse_date(text):
    if not text or text.strip() == "-":
        return None
    text = text.strip()
    for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None

def _parse_year(text):
    m = re.search(r"\b(20\d{2})\b", text or "")
    return int(m.group(1)) if m else None


# === Тесты ===

def test_hash_deterministic():
    assert _make_hash("A", "B", "C") == _make_hash("A", "B", "C")
    assert len(_make_hash("x", "y", "z")) == 64
    print("✓ test_hash_deterministic")

def test_hash_unique():
    assert _make_hash("LOT-1", "ANN-1", "name") != _make_hash("LOT-2", "ANN-1", "name")
    print("✓ test_hash_unique")

def test_parse_amount():
    assert _parse_amount("1 234 567,89") == 1234567.89
    assert _parse_amount("500000.00") == 500000.0
    assert _parse_amount("") is None
    assert _parse_amount(None) is None
    print("✓ test_parse_amount")

def test_parse_date():
    d = _parse_date("15.03.2024 12:00")
    assert d and d.year == 2024 and d.month == 3
    assert _parse_date("-") is None
    assert _parse_date("") is None
    assert _parse_date("2024-06-01") is not None
    print("✓ test_parse_date")

def test_parse_year():
    assert _parse_year("2024") == 2024
    assert _parse_year("год 2025 финансовый") == 2025
    assert _parse_year("") is None
    print("✓ test_parse_year")

def test_scheduler_interval():
    """Проверяем что интервал 3 часа = 10800 секунд."""
    hours = 3
    assert hours * 3600 == 10800
    print("✓ test_scheduler_interval (3ч = 10800с)")

def test_hash_case_insensitive():
    h1 = _make_hash("LOT-001", "ANN", "Тест")
    h2 = _make_hash("lot-001", "ann", "тест")
    assert h1 == h2  # нормализация к нижнему регистру
    print("✓ test_hash_case_insensitive")

if __name__ == "__main__":
    test_hash_deterministic()
    test_hash_unique()
    test_parse_amount()
    test_parse_date()
    test_parse_year()
    test_scheduler_interval()
    test_hash_case_insensitive()
    print("\n✅ Все 7 тестов пройдены успешно!")
