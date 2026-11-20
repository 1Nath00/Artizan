"""Persist normalized object detections for images.

Revision ID: b7c8d9e0f1a2
Revises: f8b2c4d6e1a3
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "f8b2c4d6e1a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("images", sa.Column("detecciones", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("images", "detecciones")
