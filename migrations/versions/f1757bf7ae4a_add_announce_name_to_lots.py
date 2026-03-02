"""add announce_name to lots

Revision ID: f1757bf7ae4a
Revises: eabc06214e81
Create Date: 2026-03-02 08:19:24.433821

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1757bf7ae4a'
down_revision: Union[str, None] = 'eabc06214e81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "lots",
        sa.Column("announce_name", sa.Text(), nullable=True)
    )

def downgrade():
    op.drop_column("lots", "announce_name")