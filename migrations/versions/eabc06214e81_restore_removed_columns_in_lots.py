"""Restore removed columns in lots

Revision ID: eabc06214e81
Revises: 0002
Create Date: 2026-02-25 07:42:56.334433

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'eabc06214e81'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lots",
        sa.Column("announce_number", sa.String(100), nullable=True, comment="Номер объявления"),
    )

    op.add_column(
        "lots",
        sa.Column("subject_type", sa.String(50), nullable=True, comment="Товар/Услуга/Работа"),
    )

    op.add_column(
        "lots",
        sa.Column("customer_name", sa.Text(), nullable=True, comment="Заказчик"),
    )

    op.add_column(
        "lots",
        sa.Column("customer_bin", sa.String(20), nullable=True, comment="БИН заказчика"),
    )

    op.add_column(
        "lots",
        sa.Column("deadline_date", sa.DateTime(), nullable=True, comment="Окончание приема"),
    )

    op.add_column(
        "lots",
        sa.Column("publication_date", sa.DateTime(), nullable=True, comment="Дата публикации"),
    )

    op.add_column(
        "lots",
        sa.Column("financial_year", sa.Integer(), nullable=True, comment="Финансовый год"),
    )

    op.add_column(
        "lots",
        sa.Column("delivery_place", sa.Text(), nullable=True, comment="Место поставки"),
    )

    # Индексы
    op.create_index("ix_announce_number", "lots", ["announce_number"])
    op.create_index("ix_publication_date", "lots", ["publication_date"])
    op.create_index("ix_customer_bin", "lots", ["customer_bin"])


def downgrade() -> None:
    op.drop_index("ix_customer_bin", table_name="lots")
    op.drop_index("ix_publication_date", table_name="lots")
    op.drop_index("ix_announce_number", table_name="lots")

    op.drop_column("lots", "delivery_place")
    op.drop_column("lots", "financial_year")
    op.drop_column("lots", "publication_date")
    op.drop_column("lots", "deadline_date")
    op.drop_column("lots", "customer_bin")
    op.drop_column("lots", "customer_name")
    op.drop_column("lots", "subject_type")
    op.drop_column("lots", "announce_number")
