"""Add announce_name and quantity columns
Revision ID: 0002
Revises: 0001
Create Date: 2024-02-24 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_column("lots", "quantity")
    op.drop_column("lots", "announce_name")
