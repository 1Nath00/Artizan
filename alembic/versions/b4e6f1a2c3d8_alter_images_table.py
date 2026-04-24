"""alter images table: replace binary storage with url-based schema

Revision ID: b4e6f1a2c3d8
Revises: a3f5c9b2d1e7
Create Date: 2026-04-24 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b4e6f1a2c3d8"
down_revision: Union[str, Sequence[str], None] = "a3f5c9b2d1e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # La tabla images cambia completamente de estructura (binary→url).
    # Se eliminan todas las filas para poder agregar las FK sin violaciones.
    op.execute("DELETE FROM images")

    with op.batch_alter_table("images") as batch_op:
        # Drop indexes before dropping their columns
        batch_op.drop_index("ix_images_filename")
        batch_op.drop_index("ix_images_uploaded_by")

        # Drop old columns
        batch_op.drop_column("filename")
        batch_op.drop_column("original_name")
        batch_op.drop_column("content_type")
        batch_op.drop_column("size")
        batch_op.drop_column("uploaded_by")
        batch_op.drop_column("content")

        # Rename created_at -> creado_en
        batch_op.alter_column("created_at", new_column_name="creado_en")

        # Add new columns (server_default handles existing rows)
        batch_op.add_column(
            sa.Column("usuario_id", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("imagen_url", sa.Text(), nullable=False, server_default="")
        )
        batch_op.add_column(
            sa.Column("categoria_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("titulo", sa.String(255), nullable=True)
        )
        batch_op.add_column(
            sa.Column("descripcion", sa.Text(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "estado",
                sa.String(20),
                nullable=False,
                server_default="pendiente",
            )
        )

        # Foreign keys
        batch_op.create_foreign_key(
            "fk_images_usuario_id", "users", ["usuario_id"], ["id"]
        )
        batch_op.create_foreign_key(
            "fk_images_categoria_id",
            "categorias",
            ["categoria_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("images") as batch_op:
        batch_op.drop_constraint("fk_images_usuario_id", type_="foreignkey")
        batch_op.drop_constraint("fk_images_categoria_id", type_="foreignkey")

        batch_op.drop_column("estado")
        batch_op.drop_column("descripcion")
        batch_op.drop_column("titulo")
        batch_op.drop_column("categoria_id")
        batch_op.drop_column("imagen_url")
        batch_op.drop_column("usuario_id")

        batch_op.alter_column("creado_en", new_column_name="created_at")

        batch_op.add_column(sa.Column("filename", sa.String(), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("original_name", sa.String(), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("content_type", sa.String(), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("size", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("uploaded_by", sa.String(), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("content", sa.LargeBinary(), nullable=False, server_default=b""))

        batch_op.create_index("ix_images_filename", ["filename"], unique=False)
        batch_op.create_index("ix_images_uploaded_by", ["uploaded_by"], unique=False)
