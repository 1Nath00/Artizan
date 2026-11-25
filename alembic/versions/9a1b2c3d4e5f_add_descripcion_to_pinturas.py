"""Add descripcion to pinturas.

Revision ID: 9a1b2c3d4e5f
Revises: c43559ff813c
Create Date: 2026-11-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a1b2c3d4e5f"
down_revision: Union[str, Sequence[str], None] = "c43559ff813c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("pinturas", sa.Column("descripcion", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("pinturas", "descripcion")
