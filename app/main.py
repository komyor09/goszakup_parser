"""
Точка входа микросервиса.

Запуск:
  python -m app.main            # планировщик (каждые 3 часа)
  python -m app.main --run-once # однократный запуск
"""

import sys
import signal
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

from app.config import PARSE_INTERVAL_HOURS
from app.logger import get_logger
from app.service import run_parse_job

logger = get_logger("goszakup.main")


def job_listener(event):
    if event.exception:
        logger.error(f"Задача завершилась с ошибкой: {event.exception}")
    else:
        logger.info("Задача успешно выполнена")


def handle_shutdown(sig, frame):
    logger.info("Получен сигнал завершения, останавливаем планировщик...")
    sys.exit(0)


def start_scheduler():
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    scheduler = BlockingScheduler(timezone="Asia/Almaty")
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    scheduler.add_job(
        run_parse_job,
        trigger="interval",
        hours=PARSE_INTERVAL_HOURS,
        id="parse_lots",
        name="GosZakup Lot Parser",
        max_instances=1,
        coalesce=True,
    )

    logger.info(
        f"Планировщик запущен. Интервал: {PARSE_INTERVAL_HOURS} ч. "
        f"Следующий запуск — через {PARSE_INTERVAL_HOURS} ч."
    )
    logger.info("Первый запуск выполняем сразу...")

    # Первый запуск немедленно
    run_parse_job()

    logger.info("Ожидаем следующего запуска по расписанию...")
    scheduler.start()


if __name__ == "__main__":
    if "--run-once" in sys.argv:
        logger.info("Режим: однократный запуск")
        run_parse_job()
    else:
        start_scheduler()
