"""merge object detections and pinturas migrations

Revision ID: c43559ff813c
Revises: b7c8d9e0f1a2, e5f75d534e84
Create Date: 2026-11-18 09:01:59.745429

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c43559ff813c'
down_revision: Union[str, Sequence[str], None] = ('b7c8d9e0f1a2', 'e5f75d534e84')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
