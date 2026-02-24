"""Initial schema: lots and parse_runs

Revision ID: 0001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("unique_hash", sa.String(64), nullable=False, comment="SHA256 уникальный хеш"),
        sa.Column("lot_number", sa.String(100), nullable=True, comment="Номер лота"),
        sa.Column("announce_number", sa.String(100), nullable=True, comment="Номер объявления"),
        sa.Column("lot_name", sa.Text(), nullable=True, comment="Наименование лота"),
        sa.Column("subject_type", sa.String(50), nullable=True, comment="Товар/Услуга/Работа"),
        sa.Column("status", sa.String(200), nullable=True, comment="Статус"),
        sa.Column("purchase_method", sa.String(200), nullable=True, comment="Способ закупки"),
        sa.Column("customer_name", sa.Text(), nullable=True, comment="Заказчик"),
        sa.Column("customer_bin", sa.String(20), nullable=True, comment="БИН заказчика"),
        sa.Column("purchase_amount", sa.Numeric(20, 2), nullable=True, comment="Сумма (KZT)"),
        sa.Column("deadline_date", sa.DateTime(), nullable=True, comment="Окончание приема"),
        sa.Column("publication_date", sa.DateTime(), nullable=True, comment="Дата публикации"),
        sa.Column("financial_year", sa.Integer(), nullable=True, comment="Финансовый год"),
        sa.Column("delivery_place", sa.Text(), nullable=True, comment="Место поставки"),
        sa.Column("lot_url", sa.Text(), nullable=True, comment="URL лота"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("raw_data", sa.Text(), nullable=True, comment="Сырые данные JSON"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("unique_hash", name="uq_lot_hash"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_lot_number", "lots", ["lot_number"])
    op.create_index("ix_announce_number", "lots", ["announce_number"])
    op.create_index("ix_status", "lots", ["status"])
    op.create_index("ix_publication_date", "lots", ["publication_date"])
    op.create_index("ix_customer_bin", "lots", ["customer_bin"])
    op.create_index("ix_created_at", "lots", ["created_at"])

    op.create_table(
        "parse_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(50), default="running", comment="running/success/failed"),
        sa.Column("pages_parsed", sa.Integer(), default=0),
        sa.Column("lots_found", sa.Integer(), default=0),
        sa.Column("lots_new", sa.Integer(), default=0),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_parse_runs_started_at", "parse_runs", ["started_at"])


def downgrade() -> None:
    op.drop_table("parse_runs")
    op.drop_table("lots")
