"""add refund columns to orders

Revision ID: 20260424_0010
Revises: 20260420_0009
Create Date: 2026-04-24 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260424_0010"
down_revision: Union[str, None] = "20260420_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("refund_requested", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("orders", sa.Column("refund_note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "refund_note")
    op.drop_column("orders", "refund_requested")
