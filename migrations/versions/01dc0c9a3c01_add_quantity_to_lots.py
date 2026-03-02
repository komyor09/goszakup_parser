"""add quantity to lots

Revision ID: 01dc0c9a3c01
Revises: f1757bf7ae4a
Create Date: 2026-03-02 08:33:43.240270

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '01dc0c9a3c01'
down_revision: Union[str, None] = 'f1757bf7ae4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lots",
        sa.Column("quantity", sa.String(100), nullable=True)
    )


def downgrade() -> None:
    pass
