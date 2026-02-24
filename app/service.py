"""
Сервис: сохранение лотов в БД, логирование запусков.
"""

from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.logger import get_logger
from app.models import Lot, ParseRun
from app.parser import parse_all_lots

logger = get_logger("goszakup.service")


def run_parse_job():
    """
    Основная задача: парсим сайт и сохраняем новые лоты в БД.
    Регистрируем запуск в parse_runs.
    """
    db: Session = SessionLocal()
    run = ParseRun(started_at=datetime.utcnow(), status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    lots_found = 0
    lots_new = 0
    pages_parsed = 0

    logger.info(f"=== Старт парсинга (run_id={run.id}) ===")

    try:
        prev_page = None
        for lot_data in parse_all_lots():
            # Определяем номер страницы из raw для подсчёта
            lots_found += 1

            # Проверяем дубль по unique_hash
            existing = (
                db.query(Lot)
                .filter(Lot.unique_hash == lot_data["unique_hash"])
                .first()
            )
            if existing:
                continue

            # Новый лот
            lot = Lot(**lot_data)
            db.add(lot)
            try:
                db.commit()
                lots_new += 1
                logger.debug(
                    f"  + Новый лот: {lot_data.get('lot_number')} / "
                    f"{lot_data.get('lot_name', '')[:60]}"
                )
            except IntegrityError:
                db.rollback()
                logger.debug(f"  ~ Дубль (race): {lot_data.get('unique_hash')}")

        # Обновляем run
        run.status = "success"
        run.finished_at = datetime.utcnow()
        run.lots_found = lots_found
        run.lots_new = lots_new
        db.commit()

        logger.info(
            f"=== Парсинг завершён (run_id={run.id}): "
            f"найдено={lots_found}, новых={lots_new} ==="
        )

    except Exception as e:
        logger.exception(f"Ошибка во время парсинга: {e}")
        run.status = "failed"
        run.finished_at = datetime.utcnow()
        run.lots_found = lots_found
        run.lots_new = lots_new
        run.error_message = str(e)[:2000]
        db.commit()
        raise
    finally:
        db.close()
