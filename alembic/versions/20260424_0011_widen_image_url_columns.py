"""widen image_url columns from String(512) to Text

Signed Supabase URLs contain a JWT query-parameter and regularly exceed 512
characters, causing images to be silently dropped.  Changing to Text removes
the arbitrary limit.

Revision ID: 20260424_0011
Revises: 20260424_0010
Create Date: 2026-04-24 00:01:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260424_0011"
down_revision: Union[str, None] = "20260424_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("cart_items", "image_url", type_=sa.Text(), existing_nullable=True)
    op.alter_column("order_items", "image_url", type_=sa.Text(), existing_nullable=True)
    op.alter_column("products", "image_url", type_=sa.Text(), existing_nullable=True)


def downgrade() -> None:
    op.alter_column("products", "image_url", type_=sa.String(512), existing_nullable=True)
    op.alter_column("order_items", "image_url", type_=sa.String(512), existing_nullable=True)
    op.alter_column("cart_items", "image_url", type_=sa.String(512), existing_nullable=True)
