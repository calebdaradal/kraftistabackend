"""restore missing revision chain entry

Revision ID: 20260414_0004
Revises: 20260414_0003
Create Date: 2026-04-14 03:00:00
"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "20260414_0004"
down_revision: Union[str, None] = "20260414_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This is intentionally a no-op to restore a missing migration id.
    pass


def downgrade() -> None:
    # No schema changes were made in this revision.
    pass
