"""Use categoria_id as the painting category reference.

Revision ID: d1f6a8c9b2e4
Revises: c629b20755b2
Create Date: 2026-11-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1f6a8c9b2e4"
down_revision: Union[str, Sequence[str], None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CATEGORY_ALIASES = {
    "baroque": "barroco",
    "cubism": "cubismo",
    "impressionism": "impresionismo",
    "expressionism": "expresionismo",
    "pop art": "pop-art",
}


def _normalize(value: object) -> str:
    return str(value).strip().casefold().replace("_", " ").replace("-", " ")


def _lookup_category_id(value: object, categories: dict[str, set[int]]) -> int | None:
    label = _normalize(value)
    matches = categories.get(label)
    if matches is None:
        canonical_label = _CATEGORY_ALIASES.get(label)
        if canonical_label is not None:
            matches = categories.get(_normalize(canonical_label))

    if not matches:
        return None
    if len(matches) != 1:
        raise RuntimeError(f"El nombre de categoría '{value}' es ambiguo.")
    return next(iter(matches))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if "pinturas" not in table_names or "categorias" not in table_names:
        raise RuntimeError("Se requieren las tablas pinturas y categorias.")

    painting_columns = {column["name"] for column in inspector.get_columns("pinturas")}
    legacy_columns = [
        column for column in ("categoria", "categorias") if column in painting_columns
    ]
    if "categoria_id" not in painting_columns and not legacy_columns:
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
        category_id = row["id"]
        category_ids.add(category_id)
        for label in (row["nombre"], row["slug"]):
            category_lookup.setdefault(_normalize(label), set()).add(category_id)

    selected_columns = [paintings.c.id, paintings.c.categoria_id]
    selected_columns.extend(paintings.c[column] for column in legacy_columns)
    rows = bind.execute(sa.select(*selected_columns)).mappings()
    for row in rows:
        candidates: set[int] = set()
        existing_id = row["categoria_id"]
        if existing_id is not None:
            if existing_id not in category_ids:
                raise RuntimeError(
                    f"La pintura {row['id']} referencia una categoria_id inexistente: "
                    f"{existing_id}."
                )
            candidates.add(existing_id)

        for column in legacy_columns:
            value = row[column]
            if value is None:
                continue
            category_id = _lookup_category_id(value, category_lookup)
            if category_id is None:
                raise RuntimeError(
                    f"No se puede asociar la categoría '{value}' de la pintura {row['id']}."
                )
            candidates.add(category_id)

        if len(candidates) != 1:
            raise RuntimeError(
                f"La pintura {row['id']} no tiene una categoría única y válida."
            )
        category_id = next(iter(candidates))
        if existing_id != category_id:
            bind.execute(
                paintings.update()
                .where(paintings.c.id == row["id"])
                .values(categoria_id=category_id)
            )

    inspector = sa.inspect(bind)
    foreign_keys = inspector.get_foreign_keys("pinturas")
    matching_foreign_keys = [
        foreign_key
        for foreign_key in foreign_keys
        if foreign_key.get("constrained_columns") == ["categoria_id"]
        and foreign_key.get("referred_table") == "categorias"
        and foreign_key.get("referred_columns") == ["id"]
    ]
    has_category_fk = any(
        (foreign_key.get("options") or {}).get("ondelete", "").upper()
        not in {"SET NULL", "SET DEFAULT"}
        for foreign_key in matching_foreign_keys
    )
    indexes = inspector.get_indexes("pinturas")
    has_category_index = any(
        index.get("column_names") == ["categoria_id"] for index in indexes
    )
    legacy_indexes = [
        index["name"]
        for index in indexes
        if set(index.get("column_names") or []).intersection(legacy_columns)
    ]

    with op.batch_alter_table("pinturas") as batch_op:
        for index_name in legacy_indexes:
            batch_op.drop_index(index_name)
        if not has_category_fk:
            for foreign_key in matching_foreign_keys:
                if foreign_key.get("name") is None:
                    raise RuntimeError("No se puede reemplazar una FK sin nombre.")
                batch_op.drop_constraint(
                    foreign_key["name"],
                    type_="foreignkey",
                )
        batch_op.alter_column(
            "categoria_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        if not has_category_fk:
            batch_op.create_foreign_key(
                "fk_pinturas_categoria_id",
                "categorias",
                ["categoria_id"],
                ["id"],
            )
        if not has_category_index:
            batch_op.create_index("ix_pinturas_categoria_id", ["categoria_id"])
        for column in legacy_columns:
            batch_op.drop_column(column)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    painting_columns = {column["name"] for column in inspector.get_columns("pinturas")}
    if "categoria_id" not in painting_columns:
        return

    if "categoria" not in painting_columns:
        op.add_column("pinturas", sa.Column("categoria", sa.String(), nullable=True))

    metadata = sa.MetaData()
    paintings = sa.Table("pinturas", metadata, autoload_with=bind)
    categories_table = sa.Table("categorias", metadata, autoload_with=bind)
    category_names = dict(
        bind.execute(
            sa.select(categories_table.c.id, categories_table.c.nombre)
        ).all()
    )
    for row in bind.execute(
        sa.select(paintings.c.id, paintings.c.categoria_id)
    ).mappings():
        category_name = category_names.get(row["categoria_id"])
        if category_name is None:
            raise RuntimeError(
                f"No se puede restaurar la categoría de la pintura {row['id']}."
            )
        bind.execute(
            paintings.update()
            .where(paintings.c.id == row["id"])
            .values(categoria=category_name)
        )

    inspector = sa.inspect(bind)
    foreign_keys = [
        foreign_key
        for foreign_key in inspector.get_foreign_keys("pinturas")
        if foreign_key.get("constrained_columns") == ["categoria_id"]
        and foreign_key.get("referred_table") == "categorias"
    ]


    with op.batch_alter_table("pinturas") as batch_op:
        if "ix_pinturas_categoria" not in {
            index["name"] for index in inspector.get_indexes("pinturas")
        }:
            batch_op.create_index("ix_pinturas_categoria", ["categoria"])
        for foreign_key in foreign_keys:
            if foreign_key.get("name") is None:
                raise RuntimeError("No se puede retirar una FK sin nombre.")
            batch_op.drop_constraint(foreign_key["name"], type_="foreignkey")
        batch_op.alter_column(
            "categoria",
            existing_type=sa.String(),
            nullable=False,
        )
        batch_op.alter_column(
            "categoria_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.create_foreign_key(
            "fk_pinturas_categoria_id",
            "categorias",
            ["categoria_id"],
            ["id"],
            ondelete="SET NULL",
        )
