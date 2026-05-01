"""stub for missing revision

Revision ID: a3f5c9b2d1e7
Revises: 5f0f7ae9f142
Create Date: 2026-04-16 00:00:00.000000

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "a3f5c9b2d1e7"
down_revision: Union[str, Sequence[str], None] = "5f0f7ae9f142"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
