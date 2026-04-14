"""add product variation columns

Revision ID: 20260414_0003
Revises: 20260414_0002
Create Date: 2026-04-14 02:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260414_0003"
down_revision: Union[str, None] = "20260414_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("primary_variation", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("products", sa.Column("secondary_variation", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("products", sa.Column("tertiary_variation", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "tertiary_variation")
    op.drop_column("products", "secondary_variation")
    op.drop_column("products", "primary_variation")
