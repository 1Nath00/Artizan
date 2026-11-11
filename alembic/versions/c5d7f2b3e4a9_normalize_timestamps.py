"""normalize timestamps: rename creado_en/actualizado_en to created_at/updated_at, add updated_at

Revision ID: c5d7f2b3e4a9
Revises: b4e6f1a2c3d8
Create Date: 2026-04-24 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c5d7f2b3e4a9"
down_revision: Union[str, Sequence[str], None] = "b4e6f1a2c3d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NOW = sa.func.now()


def upgrade() -> None:
    """Upgrade schema."""
    # --- images ---
    # creado_en fue renombrado a created_at en b4e6f1a2c3d8, solo agregar updated_at
    op.add_column("images", sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))

    # --- categorias ---
    op.alter_column("categorias", "creado_en", new_column_name="created_at")
    op.add_column("categorias", sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))

    # --- pinturas ---
    op.alter_column("pinturas", "creado_en", new_column_name="created_at")
    op.alter_column("pinturas", "actualizado_en", new_column_name="updated_at")

    # --- users ---
    op.add_column("users", sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))


def downgrade() -> None:
    """Downgrade schema."""
    # --- users ---
    op.drop_column("users", "updated_at")

    # --- pinturas ---
    op.alter_column("pinturas", "updated_at", new_column_name="actualizado_en")
    op.alter_column("pinturas", "created_at", new_column_name="creado_en")

    # --- categorias ---
    op.drop_column("categorias", "updated_at")
    op.alter_column("categorias", "created_at", new_column_name="creado_en")

    # --- images ---
    op.drop_column("images", "updated_at")
