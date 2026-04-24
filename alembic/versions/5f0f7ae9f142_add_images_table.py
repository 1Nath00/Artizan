"""add images table

Revision ID: 5f0f7ae9f142
Revises: bf477bb5b30a
Create Date: 2026-04-16 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "5f0f7ae9f142"
down_revision: Union[str, Sequence[str], None] = "bf477bb5b30a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("filename", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("original_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("content_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("uploaded_by", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_images_filename"), "images", ["filename"], unique=False)
    op.create_index(op.f("ix_images_uploaded_by"), "images", ["uploaded_by"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_images_uploaded_by"), table_name="images")
    op.drop_index(op.f("ix_images_filename"), table_name="images")
    op.drop_table("images")
