"""refactor product info dimensions and weight fields

Revision ID: 20260415_0006
Revises: 20260415_0005
Create Date: 2026-04-15 15:10:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260415_0006"
down_revision: Union[str, None] = "20260415_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("dimension_width_cm", sa.Numeric(10, 2), nullable=True))
    op.add_column("products", sa.Column("dimension_height_cm", sa.Numeric(10, 2), nullable=True))
    op.add_column("products", sa.Column("dimension_length_cm", sa.Numeric(10, 2), nullable=True))
    op.add_column("products", sa.Column("weight_kg", sa.Numeric(10, 3), nullable=True))

    op.execute(
        """
        UPDATE products
        SET
          dimension_width_cm = NULLIF(dimensions->>'width', '')::numeric,
          dimension_height_cm = NULLIF(dimensions->>'height', '')::numeric,
          dimension_length_cm = NULLIF(dimensions->>'depth', '')::numeric,
          weight_kg = weight
        WHERE dimensions IS NOT NULL OR weight IS NOT NULL
        """
    )

    op.drop_column("products", "dimensions")
    op.drop_column("products", "weight")


def downgrade() -> None:
    op.add_column("products", sa.Column("dimensions", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("products", sa.Column("weight", sa.Numeric(10, 3), nullable=True))

    op.execute(
        """
        UPDATE products
        SET
          dimensions = jsonb_build_object(
            'width', COALESCE(dimension_width_cm::text, ''),
            'height', COALESCE(dimension_height_cm::text, ''),
            'depth', COALESCE(dimension_length_cm::text, '')
          ),
          weight = weight_kg
        """
    )

    op.drop_column("products", "weight_kg")
    op.drop_column("products", "dimension_length_cm")
    op.drop_column("products", "dimension_height_cm")
    op.drop_column("products", "dimension_width_cm")
