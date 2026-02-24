"""
Парсер реестра лотов goszakup.gov.kz.

Использует Selenium для рендеринга JS-страниц.
Поддерживает пагинацию: обходит все страницы до последней.
"""

import hashlib
import json
import re
import time
from datetime import datetime
from typing import Generator, Optional

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from app.config import BASE_URL, HEADLESS, MAX_PAGES, PAGE_LOAD_TIMEOUT
from app.logger import get_logger

logger = get_logger("goszakup.parser")


def _build_driver() -> webdriver.Chrome:
    """Создать и вернуть Chrome WebDriver."""
    opts = Options()
    if HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--lang=ru-RU")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    return driver


def _make_hash(lot_number: str, announce_number: str, lot_name: str) -> str:
    """Генерируем уникальный хеш SHA256 на основе ключевых полей."""
    raw = f"{lot_number}|{announce_number}|{lot_name}".lower().strip()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _parse_amount(text: str) -> Optional[float]:
    """Парсим сумму из строки вида '1 234 567,89' или '1234567.89'."""
    if not text:
        return None
    cleaned = re.sub(r"[^\d,.]", "", text).replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_date(text: str) -> Optional[datetime]:
    """Парсим дату из разных форматов."""
    if not text or text.strip() == "-":
        return None
    text = text.strip()
    for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _parse_year(text: str) -> Optional[int]:
    """Извлекаем год из строки."""
    m = re.search(r"\b(20\d{2})\b", text or "")
    return int(m.group(1)) if m else None


def _wait_for_table(driver: webdriver.Chrome) -> bool:
    """Ждём загрузки таблицы лотов."""
    try:
        WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
        )
        return True
    except Exception:
        # Попробуем подождать через JS
        time.sleep(5)
        return False


def _extract_rows_from_page(driver: webdriver.Chrome) -> list[dict]:
    """
    Извлечь все строки таблицы со текущей страницы.
    Адаптивный парсер: определяем колонки по заголовкам.
    """
    soup = BeautifulSoup(driver.page_source, "lxml")

    table = soup.find("table")
    if not table:
        logger.warning("Таблица не найдена на странице")
        return []

    # Определяем заголовки
    header_row = table.find("thead")
    headers = []
    if header_row:
        headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]
    logger.debug(f"Заголовки таблицы: {headers}")

    rows = []
    tbody = table.find("tbody")
    if not tbody:
        return []

    for tr in tbody.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue

        cell_texts = [c.get_text(separator=" ", strip=True) for c in cells]
        # Получаем ссылку из строки (если есть)
        link_tag = tr.find("a", href=True)
        lot_url = None
        if link_tag:
            href = link_tag["href"]
            if href.startswith("http"):
                lot_url = href
            else:
                lot_url = "https://www.goszakup.gov.kz" + href

        # Маппинг по индексам (типичная структура реестра лотов):
        # 0 - №
        # 1 - Номер лота
        # 2 - Номер объявления
        # 3 - Наименование лота
        # 4 - Заказчик
        # 5 - Способ закупки
        # 6 - Статус
        # 7 - Сумма
        # 8 - Дата окончания
        # (порядок может меняться, парсим по максимуму)

        n = len(cell_texts)

        def safe(i):
            return cell_texts[i].strip() if i < n else ""

        # Пробуем динамический маппинг через заголовки
        if headers and len(headers) == n:
            row_dict = dict(zip(headers, cell_texts))
        else:
            # Fallback — по позиции
            row_dict = {}
            for i, txt in enumerate(cell_texts):
                row_dict[f"col_{i}"] = txt

        row_dict["__url__"] = lot_url
        row_dict["__raw__"] = cell_texts
        rows.append(row_dict)

    return rows


def _normalize_row(row: dict, headers: list[str]) -> dict:
    """
    Нормализуем строку таблицы в структурированный словарь.
    Поддерживаем как именованные заголовки, так и col_N формат.
    """
    def find_val(*keys) -> str:
        """Ищем значение по списку возможных ключей (частичное совпадение)."""
        for k in keys:
            for h in row:
                if k.lower() in h.lower():
                    v = row[h]
                    if isinstance(v, str) and v.strip():
                        return v.strip()
        # fallback по col_N
        mapping = {
            "номер лота": 1,
            "номер объявления": 2,
            "наименование": 3,
            "заказчик": 4,
            "способ": 5,
            "статус": 6,
            "сумма": 7,
            "окончани": 8,
        }
        for k in keys:
            for kw, idx in mapping.items():
                if kw in k.lower():
                    v = row.get(f"col_{idx}", "")
                    if v:
                        return v
        return ""

    lot_number = find_val("номер лота", "lot_number", "лот №")
    announce_number = find_val("номер объявления", "объявлени", "announce")
    lot_name = find_val("наименование", "описание", "лота", "name")
    customer = find_val("заказчик", "customer", "организаци")
    method = find_val("способ", "метод", "method")
    status = find_val("статус", "status")
    amount_raw = find_val("сумма", "amount", "цена", "стоимость")
    deadline_raw = find_val("окончани", "deadline", "прием до", "прием по")
    pub_date_raw = find_val("публикац", "дата", "опубликован")
    year_raw = find_val("финансов", "год")
    place = find_val("место", "поставк", "регион")

    # BIN из имени заказчика (формат: "Название (БИН: 123456789012)")
    customer_bin = None
    bin_match = re.search(r"[\(\s](\d{12})[\)\s]", customer or "")
    if bin_match:
        customer_bin = bin_match.group(1)

    # Уникальный хеш
    unique_hash = _make_hash(lot_number, announce_number, lot_name)

    return {
        "unique_hash": unique_hash,
        "lot_number": lot_number or None,
        "announce_number": announce_number or None,
        "lot_name": lot_name or None,
        "subject_type": None,  # из фильтра, обычно не в таблице
        "status": status or None,
        "purchase_method": method or None,
        "customer_name": customer or None,
        "customer_bin": customer_bin,
        "purchase_amount": _parse_amount(amount_raw),
        "deadline_date": _parse_date(deadline_raw),
        "publication_date": _parse_date(pub_date_raw),
        "financial_year": _parse_year(year_raw),
        "delivery_place": place or None,
        "lot_url": row.get("__url__"),
        "raw_data": json.dumps(row.get("__raw__", []), ensure_ascii=False),
    }


def _get_total_pages(driver: webdriver.Chrome) -> int:
    """Определяем количество страниц пагинации."""
    try:
        soup = BeautifulSoup(driver.page_source, "lxml")
        # Ищем пагинацию (Bootstrap-style: ul.pagination li a)
        pagination = soup.find("ul", class_=re.compile(r"pagination", re.I))
        if not pagination:
            return 1

        page_numbers = []
        for a in pagination.find_all("a"):
            txt = a.get_text(strip=True)
            if txt.isdigit():
                page_numbers.append(int(txt))

        # Также ищем в кнопке "последняя" / text содержащий число
        last_link = pagination.find("a", string=re.compile(r"(посл|last|»)", re.I))
        if last_link:
            href = last_link.get("href", "")
            m = re.search(r"[?&]page=(\d+)", href)
            if m:
                page_numbers.append(int(m.group(1)))

        return max(page_numbers) if page_numbers else 1
    except Exception as e:
        logger.warning(f"Не удалось определить число страниц: {e}")
        return 1


def _navigate_to_page(driver: webdriver.Chrome, page: int) -> bool:
    """Переходим на нужную страницу."""
    url = f"{BASE_URL}?page={page}"
    try:
        driver.get(url)
        return _wait_for_table(driver)
    except Exception as e:
        logger.error(f"Ошибка при переходе на страницу {page}: {e}")
        return False


def parse_all_lots() -> Generator[dict, None, None]:
    """
    Генератор: обходит все страницы реестра лотов и отдаёт нормализованные строки.
    """
    driver = _build_driver()
    logger.info("WebDriver инициализирован")

    try:
        # Загружаем первую страницу
        logger.info(f"Загружаем {BASE_URL}")
        driver.get(BASE_URL)
        loaded = _wait_for_table(driver)

        if not loaded:
            logger.warning("Таблица не загрузилась на первой странице. Проверьте сайт.")

        total_pages = _get_total_pages(driver)
        logger.info(f"Всего страниц: {total_pages}")

        if MAX_PAGES > 0:
            total_pages = min(total_pages, MAX_PAGES)
            logger.info(f"Ограничение MAX_PAGES={MAX_PAGES}, обработаем {total_pages} стр.")

        headers: list[str] = []

        for page_num in range(1, total_pages + 1):
            logger.info(f"Парсим страницу {page_num}/{total_pages}")

            if page_num > 1:
                ok = _navigate_to_page(driver, page_num)
                if not ok:
                    logger.warning(f"Страница {page_num} не загрузилась, пропускаем")
                    continue

            # Небольшая пауза, чтобы не нагружать сервер
            time.sleep(2)

            rows = _extract_rows_from_page(driver)
            logger.info(f"  Страница {page_num}: найдено строк = {len(rows)}")

            # Собираем заголовки с первой страницы
            if page_num == 1 and rows:
                # headers уже внутри rows как ключи
                headers = [k for k in rows[0].keys() if not k.startswith("__")]

            for row in rows:
                normalized = _normalize_row(row, headers)
                yield normalized

    except Exception as e:
        logger.exception(f"Критическая ошибка парсера: {e}")
        raise
    finally:
        driver.quit()
        logger.info("WebDriver закрыт")
