from datetime import datetime
from sqlalchemy import (
    Column, String, Text, DateTime, Integer, Numeric,
    BigInteger, Index, UniqueConstraint
)
from app.database import Base


class Lot(Base):
    """
    Нормализованная таблица лотов государственных закупок.
    unique_hash — SHA256 от ключевых полей (lot_number + announce_number + customer_bin).
    """
    __tablename__ = "lots"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    unique_hash = Column(String(64), nullable=False, comment="SHA256 уникальный хеш лота")

    # --- Идентификаторы ---
    lot_number = Column(String(100), nullable=True, comment="Номер лота")
    announce_number = Column(String(100), nullable=True, comment="Номер объявления")

    # --- Описание лота ---
    lot_name = Column(Text, nullable=True, comment="Наименование/описание лота")
    subject_type = Column(String(50), nullable=True, comment="Предмет закупки (Товар/Услуга/Работа)")

    # --- Статус и способ ---
    status = Column(String(200), nullable=True, comment="Статус лота")
    purchase_method = Column(String(200), nullable=True, comment="Способ закупки")

    # --- Заказчик ---
    customer_name = Column(Text, nullable=True, comment="Наименование заказчика")
    customer_bin = Column(String(20), nullable=True, comment="БИН заказчика")

    # --- Финансы ---
    purchase_amount = Column(Numeric(20, 2), nullable=True, comment="Сумма закупки (KZT)")

    # --- Даты ---
    deadline_date = Column(DateTime, nullable=True, comment="Окончание приема заявок")
    publication_date = Column(DateTime, nullable=True, comment="Дата публикации")
    financial_year = Column(Integer, nullable=True, comment="Финансовый год")

    # --- Место поставки ---
    delivery_place = Column(Text, nullable=True, comment="Место поставки")

    # --- Ссылка ---
    lot_url = Column(Text, nullable=True, comment="URL страницы лота")

    # --- Служебные поля ---
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="Дата добавления в БД")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    raw_data = Column(Text, nullable=True, comment="Сырые данные строки (JSON)")

    __table_args__ = (
        UniqueConstraint("unique_hash", name="uq_lot_hash"),
        Index("ix_lot_number", "lot_number"),
        Index("ix_announce_number", "announce_number"),
        Index("ix_status", "status"),
        Index("ix_publication_date", "publication_date"),
        Index("ix_customer_bin", "customer_bin"),
        Index("ix_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<Lot(id={self.id}, lot_number={self.lot_number}, status={self.status})>"


class ParseRun(Base):
    """
    Журнал запусков парсера.
    """
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
