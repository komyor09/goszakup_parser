"""Add announce_name and quantity columns
Revision ID: 0003
Revises: 0002
Create Date: 2024-02-24 00:00:00.000000
"""

from typing import Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    columns_to_drop = [
        "quantity",
        "announce_name",
        "subject_type",
        "announce_number",
        "customer_name",
        "customer_bin",
        "deadline_date",
        "publication_date",
        "financial_year",
        "delivery_place",
    ]

    for column in columns_to_drop:
        if column_exists("lots", column):
            op.drop_column("lots", column)


def downgrade() -> None:
    op.add_column(
        "lots",
        sa.Column(
            "announce_name",
            sa.Text(),
            nullable=True,
            comment="Наименование объявления (из первой колонки)",
        ),
    )

    op.add_column(
        "lots",
        sa.Column(
            "quantity",
            sa.String(100),
            nullable=True,
            comment="Количество (колонка Кол-во)",
        ),
    )