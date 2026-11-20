"""add confianza column to images

Revision ID: f8b2c4d6e1a3
Revises: d1f6a8c9b2e4
Create Date: 2026-11-18

Persiste el porcentaje de confianza (0-1) del resultado de clasificación CNN
para las imágenes subidas por los usuarios (SCRUM-6). Nullable para mantener
compatibilidad con los registros existentes y con las subidas manuales.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f8b2c4d6e1a3"
down_revision: Union[str, Sequence[str], None] = "d1f6a8c9b2e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("images") as batch_op:
        batch_op.add_column(sa.Column("confianza", sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("images") as batch_op:
        batch_op.drop_column("confianza")
