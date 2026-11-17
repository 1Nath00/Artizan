"""Add categoria_id while retaining the legacy painting category text.

Revision ID: d1e2f3a4b5c6
Revises: c629b20755b2
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "c629b20755b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CATEGORY_ALIASES = {
    "baroque": "barroco",
    "cubism": "cubismo",
    "impressionism": "impresionismo",
    "expressionism": "expresionismo",
    "pop art": "pop art",
}


def _normalize(value: object) -> str:
    return str(value).strip().casefold().replace("_", " ").replace("-", " ")


def _category_id(value: object, categories: dict[str, set[int]]) -> int | None:
    label = _normalize(value)
    matches = categories.get(label)
    if matches is None:
        alias = _CATEGORY_ALIASES.get(label)
        if alias is not None:
            matches = categories.get(_normalize(alias))
    if not matches:
        return None
    if len(matches) != 1:
        raise RuntimeError(f"El nombre de categoría '{value}' es ambiguo.")
    return next(iter(matches))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not {"pinturas", "categorias"}.issubset(inspector.get_table_names()):
        raise RuntimeError("Se requieren las tablas pinturas y categorias.")

    painting_columns = {column["name"] for column in inspector.get_columns("pinturas")}
    legacy_columns = [
        column for column in ("categoria", "categorias") if column in painting_columns
    ]
    if not legacy_columns and "categoria_id" not in painting_columns:
        raise RuntimeError("No se encontró una columna de categoría en pinturas.")
    if "categoria_id" not in painting_columns:
        op.add_column("pinturas", sa.Column("categoria_id", sa.Integer(), nullable=True))

    metadata = sa.MetaData()
    paintings = sa.Table("pinturas", metadata, autoload_with=bind)
    categories_table = sa.Table("categorias", metadata, autoload_with=bind)
    category_ids: set[int] = set()
    category_lookup: dict[str, set[int]] = {}
    for row in bind.execute(
        sa.select(
            categories_table.c.id,
            categories_table.c.nombre,
            categories_table.c.slug,
        )
    ).mappings():
        category_ids.add(row["id"])
        for label in (row["nombre"], row["slug"]):
            category_lookup.setdefault(_normalize(label), set()).add(row["id"])

    selected_columns = [paintings.c.id, paintings.c.categoria_id]
    selected_columns.extend(paintings.c[column] for column in legacy_columns)
    for row in bind.execute(sa.select(*selected_columns)).mappings():
        existing_id = row["categoria_id"]
        if existing_id is not None:
            if existing_id not in category_ids:
                raise RuntimeError(
                    f"La pintura {row['id']} referencia una categoria_id inexistente: "
                    f"{existing_id}."
                )
            continue

        candidates = set()
        for column in legacy_columns:
            value = row[column]
            if value is not None:
                category_id = _category_id(value, category_lookup)
                if category_id is None:
                    raise RuntimeError(
                        f"No se puede asociar la categoría '{value}' "
                        f"de la pintura {row['id']}."
                    )
                candidates.add(category_id)
        if len(candidates) != 1:
            raise RuntimeError(
                f"La pintura {row['id']} no tiene una categoría única y válida."
            )
        bind.execute(
            paintings.update()
            .where(paintings.c.id == row["id"])
            .values(categoria_id=next(iter(candidates)))
        )

    inspector = sa.inspect(bind)
    has_category_fk = any(
        foreign_key.get("constrained_columns") == ["categoria_id"]
        and foreign_key.get("referred_table") == "categorias"
        and foreign_key.get("referred_columns") == ["id"]
        for foreign_key in inspector.get_foreign_keys("pinturas")
    )
    has_category_index = any(
        index.get("column_names") == ["categoria_id"]
        for index in inspector.get_indexes("pinturas")
    )
    with op.batch_alter_table("pinturas") as batch_op:
        if not has_category_fk:
            batch_op.create_foreign_key(
                "fk_pinturas_categoria_id",
                "categorias",
                ["categoria_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if not has_category_index:
            batch_op.create_index("ix_pinturas_categoria_id", ["categoria_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "categoria_id" not in {
        column["name"] for column in inspector.get_columns("pinturas")
    }:
        return

    indexes = [
        index["name"]
        for index in inspector.get_indexes("pinturas")
        if index.get("column_names") == ["categoria_id"]
    ]
    foreign_keys = [
        foreign_key
        for foreign_key in inspector.get_foreign_keys("pinturas")
        if foreign_key.get("constrained_columns") == ["categoria_id"]
        and foreign_key.get("referred_table") == "categorias"
    ]

    with op.batch_alter_table("pinturas") as batch_op:
        for index_name in indexes:
            batch_op.drop_index(index_name)
        for foreign_key in foreign_keys:
            if foreign_key.get("name") is None:
                raise RuntimeError("No se puede retirar una FK sin nombre.")
            batch_op.drop_constraint(foreign_key["name"], type_="foreignkey")
        batch_op.drop_column("categoria_id")
