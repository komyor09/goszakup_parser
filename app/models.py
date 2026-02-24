from datetime import datetime
from sqlalchemy import (
    Column, String, Text, DateTime, Integer,
    Numeric, BigInteger, Index, UniqueConstraint
)
from app.database import Base


class Lot(Base):
    """
    Нормализованная таблица лотов государственных закупок.

    Структура таблицы на сайте (6 колонок):
      0: № лота | Наименование объявления | Заказчик
      1: Наименование и описание лота
      2: Кол-во
      3: Сумма, тг.
      4: Способ закупки
      5: Статус

    unique_hash = SHA256(lot_number + announce_number + lot_name)
    """
    __tablename__ = "lots"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    unique_hash = Column(String(64), nullable=False, comment="SHA256 хеш для дедупликации")

    # Идентификаторы
    lot_number = Column(String(100), nullable=True, comment="№ лота (напр. 82073905-ЗЦП1)")
    announce_number = Column(String(100), nullable=True, comment="Номер объявления (напр. 16413510-1)")
    announce_name = Column(Text, nullable=True, comment="Наименование объявления")

    # Лот
    lot_name = Column(Text, nullable=True, comment="Наименование и описание лота")
    subject_type = Column(String(50), nullable=True, comment="Товар/Услуга/Работа")
    quantity = Column(String(100), nullable=True, comment="Количество")

    # Статус и способ
    status = Column(String(200), nullable=True, comment="Статус лота")
    purchase_method = Column(String(200), nullable=True, comment="Способ закупки")

    # Заказчик
    customer_name = Column(Text, nullable=True, comment="Наименование заказчика")
    customer_bin = Column(String(20), nullable=True, comment="БИН заказчика")

    # Финансы
    purchase_amount = Column(Numeric(20, 2), nullable=True, comment="Сумма закупки (KZT)")

    # Даты
    deadline_date = Column(DateTime, nullable=True, comment="Окончание приёма заявок")
    publication_date = Column(DateTime, nullable=True, comment="Дата публикации")
    financial_year = Column(Integer, nullable=True, comment="Финансовый год")

    # Прочее
    delivery_place = Column(Text, nullable=True, comment="Место поставки")
    lot_url = Column(Text, nullable=True, comment="URL страницы лота")

    # Служебные
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    raw_data = Column(Text, nullable=True, comment="JSON со всеми сырыми данными строки")

    __table_args__ = (
        UniqueConstraint("unique_hash", name="uq_lot_hash"),
        Index("ix_lot_number", "lot_number"),
        Index("ix_announce_number", "announce_number"),
        Index("ix_status", "status"),
        Index("ix_publication_date", "publication_date"),
        Index("ix_customer_bin", "customer_bin"),
        Index("ix_created_at", "created_at"),
        Index("ix_purchase_method", "purchase_method"),
    )

    def __repr__(self):
        return f"<Lot(id={self.id}, lot_number={self.lot_number!r}, status={self.status!r})>"


class ParseRun(Base):
    """Журнал каждого запуска парсера."""
    __tablename__ = "parse_runs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="running", comment="running / success / failed")
    pages_parsed = Column(Integer, default=0)
    lots_found = Column(Integer, default=0)
    lots_new = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_parse_runs_started_at", "started_at"),
    )

    def __repr__(self):
        return (
            f"<ParseRun(id={self.id}, status={self.status!r}, "
            f"lots_new={self.lots_new})>"
        )