"""
Сервис: сохранение лотов в БД + журналирование запусков.
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
    Основная задача планировщика.
    Парсим ВСЕ страницы реестра лотов и сохраняем НОВЫЕ в БД.
    Дубли определяются по unique_hash — пропускаем без ошибки.
    """
    db: Session = SessionLocal()
    run = ParseRun(started_at=datetime.utcnow(), status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    lots_found = 0
    lots_new = 0
    pages_seen = set()

    logger.info(f"╔═══ СТАРТ ПАРСИНГА (run_id={run.id}) ═══")

    try:
        for lot_data in parse_all_lots():
            lots_found += 1

            # Проверка дубля
            exists = (
                db.query(Lot.id)
                .filter(Lot.unique_hash == lot_data["unique_hash"])
                .first()
            )
            if exists:
                continue

            # Сохраняем новый лот
            lot = Lot(
                unique_hash=lot_data["unique_hash"],
                lot_number=lot_data.get("lot_number"),
                announce_number=lot_data.get("announce_number"),
                announce_name=lot_data.get("announce_name"),
                lot_name=lot_data.get("lot_name"),
                subject_type=lot_data.get("subject_type"),
                quantity=lot_data.get("quantity"),
                status=lot_data.get("status"),
                purchase_method=lot_data.get("purchase_method"),
                customer_name=lot_data.get("customer_name"),
                customer_bin=lot_data.get("customer_bin"),
                purchase_amount=lot_data.get("purchase_amount"),
                deadline_date=lot_data.get("deadline_date"),
                publication_date=lot_data.get("publication_date"),
                financial_year=lot_data.get("financial_year"),
                delivery_place=lot_data.get("delivery_place"),
                lot_url=lot_data.get("lot_url"),
                raw_data=lot_data.get("raw_data"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(lot)
            try:
                db.commit()
                lots_new += 1
                if lots_new % 100 == 0:
                    logger.info(f"  Сохранено новых лотов: {lots_new} (всего обработано: {lots_found})")
            except IntegrityError:
                db.rollback()

        # Финал
        run.status = "success"
        run.finished_at = datetime.utcnow()
        run.lots_found = lots_found
        run.lots_new = lots_new
        db.commit()

        duration = (run.finished_at - run.started_at).seconds
        logger.info(
            f"╚═══ ПАРСИНГ ЗАВЕРШЁН (run_id={run.id}) | "
            f"найдено={lots_found} | новых={lots_new} | "
            f"время={duration}с ═══"
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