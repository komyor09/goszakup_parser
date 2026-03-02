"""
Парсер реестра лотов goszakup.gov.kz

Реальная структура таблицы (6 колонок):
  [0] № лота + номер объявления + заказчик (всё в одной ячейке через многострочный HTML)
  [1] Наименование и описание лота (ссылка)
  [2] Кол-во
  [3] Сумма, тг.
  [4] Способ закупки
  [5] Статус

Пагинация: ?page=N, максимум 10 000 записей (200 страниц по 50).
Парсер использует Selenium т.к. сайт рендерится через JavaScript.
"""

import hashlib
import json
import re
import time
from datetime import datetime
from typing import Generator, Optional

from bs4 import BeautifulSoup, Tag
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


# ---------------------------------------------------------------------------
# WebDriver
# ---------------------------------------------------------------------------

def _build_driver() -> webdriver.Chrome:
    opts = Options()

    if HEADLESS:
        opts.add_argument("--headless=new")

    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--lang=ru-RU")

    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

    return driver


def _wait_for_table(driver: webdriver.Chrome) -> bool:
    """Ждём пока таблица лотов отрендерится JS-ом."""
    try:
        WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "table tbody tr td")
            )
        )
        # Дополнительно ждём исчезновения спиннера «Подождите, идет загрузка»
        time.sleep(2)
        return True
    except Exception:
        time.sleep(5)
        return False


# ---------------------------------------------------------------------------
# Хеш и вспомогательные утилиты
# ---------------------------------------------------------------------------

def _make_hash(lot_number: str, announce_number: str, lot_name: str) -> str:
    raw = f"{lot_number}|{announce_number}|{lot_name}".lower().strip()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _parse_amount(text: str) -> Optional[float]:
    if not text:
        return None
    cleaned = re.sub(r"[^\d,.]", "", text.strip()).replace(",", ".")
    # Убираем лишние точки (разделители тысяч в формате "1.234.567.89")
    parts = cleaned.split(".")
    if len(parts) > 2:
        cleaned = "".join(parts[:-1]) + "." + parts[-1]
    try:
        val = float(cleaned)
        return val if val > 0 else None
    except ValueError:
        return None


def _clean_text(tag: Optional[Tag]) -> str:
    if tag is None:
        return ""
    return tag.get_text(separator=" ", strip=True)


# ---------------------------------------------------------------------------
# Парсинг одной строки таблицы
# ---------------------------------------------------------------------------

def _parse_row(tr: Tag) -> Optional[dict]:
    """
    Разбираем строку таблицы реестра лотов.

    Структура ячейки [0] (первая колонка):
      - Жирный текст: № лота (напр. "82073905-ЗЦП1")
      - Ссылка на объявление: текст типа "16413510-1 Приобретение..."
      - После ссылки: "Заказчик: ..."

    Структура ячейки [1] (вторая колонка):
      - Ссылка: наименование лота
    """
    cells = tr.find_all("td", recursive=False)
    if len(cells) < 6:
        return None

    # --- Ячейка 0: № лота, объявление, заказчик ---
    cell0 = cells[0]

    # № лота — обычно первый жирный текст или первая строка
    lot_number = ""
    bold_tags = cell0.find_all(["b", "strong"])
    if bold_tags:
        lot_number = bold_tags[0].get_text(strip=True)
    if not lot_number:
        # Fallback: первая строка текста до переноса
        raw_text = cell0.get_text(separator="\n", strip=True)
        lot_number = raw_text.split("\n")[0].strip()

    # Номер объявления — из href ссылки вида /ru/announce/index/16413510
    announce_number = ""
    announce_url = ""
    lot_url = ""
    announce_link = cell0.find("a", href=re.compile(r"/announce/index/"))
    if announce_link:
        announce_text = announce_link.get_text(strip=True)
        # Текст: "16413510-1 Приобретение строительных товаров"
        # Берём только номер (до первого пробела)
        announce_number = announce_text.split()[0] if announce_text else ""
        href = announce_link.get("href", "")
        if href.startswith("/"):
            announce_url = "https://www.goszakup.gov.kz" + href
        else:
            announce_url = href

    # Наименование объявления (полный текст ссылки объявления)
    announce_name = announce_link.get_text(strip=True) if announce_link else ""

    # Заказчик — текст после "Заказчик:"
    customer_name = ""
    full_text = cell0.get_text(separator="\n", strip=True)
    customer_match = re.search(r"Заказчик:\s*(.+)", full_text, re.DOTALL)
    if customer_match:
        customer_name = customer_match.group(1).strip().split("\n")[0].strip()

    # --- Ячейка 1: наименование лота ---
    cell1 = cells[1]
    lot_name = ""
    lot_link = cell1.find("a", href=re.compile(r"/subpriceoffer/index/|/announce/index/"))
    if lot_link:
        lot_name = lot_link.get_text(strip=True)
        href = lot_link.get("href", "")
        if href.startswith("/"):
            lot_url = "https://www.goszakup.gov.kz" + href
        else:
            lot_url = href
    else:
        lot_name = _clean_text(cell1)

    # --- Ячейка 2: Кол-во ---
    quantity_str = _clean_text(cells[2])

    # --- Ячейка 3: Сумма, тг. ---
    amount_raw = _clean_text(cells[3])
    purchase_amount = _parse_amount(amount_raw)

    # --- Ячейка 4: Способ закупки ---
    purchase_method = _clean_text(cells[4])

    # --- Ячейка 5: Статус ---
    status = _clean_text(cells[5])

    # --- Уникальный хеш ---
    unique_hash = _make_hash(lot_number, announce_number, lot_name)

    raw_data = json.dumps(
        {
            "lot_number": lot_number,
            "announce_number": announce_number,
            "announce_name": announce_name,
            "lot_name": lot_name,
            "customer_name": customer_name,
            "quantity": quantity_str,
            "amount": amount_raw,
            "method": purchase_method,
            "status": status,
        },
        ensure_ascii=False,
    )

    return {
        "unique_hash": unique_hash,
        "lot_number": lot_number or None,
        "announce_number": announce_number or None,
        "lot_name": lot_name or None,
        "subject_type": None,
        "status": status or None,
        "purchase_method": purchase_method or None,
        "customer_name": customer_name or None,
        "customer_bin": _extract_bin(customer_name),
        "purchase_amount": purchase_amount,
        "deadline_date": None,
        "publication_date": None,
        "financial_year": None,
        "delivery_place": None,
        "lot_url": lot_url or announce_url or None,
        "raw_data": raw_data,
    }


def _extract_bin(customer_name: str) -> Optional[str]:
    """Извлекаем 12-значный БИН из названия заказчика если есть."""
    if not customer_name:
        return None
    m = re.search(r"\b(\d{12})\b", customer_name)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Пагинация
# ---------------------------------------------------------------------------

def _get_total_pages(soup: BeautifulSoup) -> int:
    """
    Определяем количество страниц.
    Сайт показывает "Показано c 1 по 50 из 10000 записей"
    Значит: ceil(total / per_page) страниц.
    """
    try:
        # Ищем текст "Показано c X по Y из Z записей"
        text = soup.get_text()
        m = re.search(r"Показано\s+c\s+\d+\s+по\s+(\d+)\s+из\s+([\d\s]+)\s+записей", text)
        if m:
            per_page = int(m.group(1))
            total = int(m.group(2).replace(" ", ""))
            import math
            pages = math.ceil(total / per_page)
            logger.info(f"Всего записей: {total}, на странице: {per_page}, страниц: {pages}")
            return pages

        # Fallback: ищем пагинацию Bootstrap
        pagination = soup.find("ul", class_=re.compile(r"pagination", re.I))
        if pagination:
            nums = [
                int(a.get_text(strip=True))
                for a in pagination.find_all("a")
                if a.get_text(strip=True).isdigit()
            ]
            if nums:
                return max(nums)
    except Exception as e:
        logger.warning(f"Не удалось определить страниц: {e}")
    return 1


def _extract_rows_from_page(driver: webdriver.Chrome) -> list[dict]:
    """Извлечь все лоты с текущей страницы."""
    soup = BeautifulSoup(driver.page_source, "lxml")

    # Ищем таблицу лотов (содержит нужные заголовки)
    target_table = None
    for table in soup.find_all("table"):
        headers_text = table.get_text()
        if "Способ закупки" in headers_text and "Статус" in headers_text:
            target_table = table
            break

    if not target_table:
        logger.warning("Таблица лотов не найдена на странице")
        return []

    tbody = target_table.find("tbody")
    if not tbody:
        return []

    results = []
    for tr in tbody.find_all("tr"):
        parsed = _parse_row(tr)
        if parsed:
            results.append(parsed)

    return results


# ---------------------------------------------------------------------------
# Основной генератор
# ---------------------------------------------------------------------------

def parse_all_lots() -> Generator[dict, None, None]:
    """
    Генератор: обходит ВСЕ страницы реестра лотов и отдаёт нормализованные лоты.
    Сайт показывает максимум 10 000 записей (200 страниц × 50 записей).
    """
    driver = _build_driver()
    logger.info("WebDriver инициализирован")

    try:
        logger.info(f"Загружаем первую страницу: {BASE_URL}")
        driver.get(BASE_URL)
        loaded = _wait_for_table(driver)

        if not loaded:
            logger.warning("Таблица не загрузилась. Ждём ещё 10 сек...")
            time.sleep(10)

        soup_first = BeautifulSoup(driver.page_source, "lxml")
        total_pages = _get_total_pages(soup_first)

        if MAX_PAGES > 0:
            total_pages = min(total_pages, MAX_PAGES)
            logger.info(f"MAX_PAGES={MAX_PAGES}, обработаем {total_pages} стр.")

        logger.info(f"Начинаем обход {total_pages} страниц...")

        for page_num in range(1, total_pages + 1):
            if page_num > 1:
                url = f"{BASE_URL}?page={page_num}"
                logger.info(f"→ Страница {page_num}/{total_pages}: {url}")
                try:
                    driver.get(url)
                    _wait_for_table(driver)
                except Exception as e:
                    logger.error(f"Ошибка загрузки страницы {page_num}: {e}")
                    time.sleep(5)
                    continue
            else:
                logger.info(f"→ Страница 1/{total_pages}")

            rows = _extract_rows_from_page(driver)
            logger.info(f"  Найдено лотов: {len(rows)}")

            if not rows:
                logger.warning(f"  Страница {page_num} пуста — останавливаем обход")
                break

            for row in rows:
                yield row

            # Пауза между страницами — не перегружаем сервер
            time.sleep(1.5)

    except Exception as e:
        logger.exception(f"Критическая ошибка парсера: {e}")
        raise
    finally:
        driver.quit()
        logger.info("WebDriver закрыт")
