"""add categorias and pinturas tables

Revision ID: a3f5c9b2d1e7
Revises: 5f0f7ae9f142
Create Date: 2026-04-24 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "a3f5c9b2d1e7"
down_revision: Union[str, Sequence[str], None] = "5f0f7ae9f142"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "categorias",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_categorias_slug"), "categorias", ["slug"], unique=True)

    op.create_table(
        "pinturas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(255), nullable=False),
        sa.Column("artista", sa.String(255), nullable=True),
        sa.Column("anio", sa.Integer(), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("categoria_id", sa.Integer(), nullable=True),
        sa.Column("imagen_url", sa.Text(), nullable=False),
        sa.Column("imagen_thumb", sa.Text(), nullable=True),
        sa.Column("destacada", sa.Boolean(), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["categoria_id"], ["categorias.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("pinturas")
    op.drop_index(op.f("ix_categorias_slug"), table_name="categorias")
    op.drop_table("categorias")
