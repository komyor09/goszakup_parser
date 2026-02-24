# GosZakup Lot Parser

Микросервис для парсинга реестра лотов с портала государственных закупок РК (goszakup.gov.kz).

## Возможности

- Парсинг всех страниц реестра лотов (с поддержкой пагинации)
- Запуск каждые 3 часа (APScheduler)
- Сохранение новых лотов в MySQL (дубли игнорируются)
- Генерация уникального ID на основе данных лота
- Полное логирование (файл + консоль)
- Миграции через Alembic
- Поддержка Docker

## Быстрый старт

### 1. Клонирование и настройка

```bash
git clone <your-repo>
cd goszakup-parser
cp .env.example .env
# Отредактируй .env — укажи данные MySQL
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка базы данных

```bash
mysql -u root -p -e "CREATE DATABASE goszakup CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
alembic upgrade head
```

### 4. Запуск

```bash
# Однократный запуск
python -m app.main --run-once

# Планировщик (каждые 3 часа)
python -m app.main

# Docker
docker-compose up -d
```

## Переменные окружения (.env)

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=goszakup
PARSE_INTERVAL_HOURS=3
HEADLESS=true
```
