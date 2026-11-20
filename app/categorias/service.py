import logging
from typing import Optional

from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.categorias.models import Categoria

logger = logging.getLogger(__name__)

# Etiquetas devueltas por el CNN -> slug de la categoría en BD.
CNN_LABEL_TO_SLUG = {
    "barroco": "barroco",
    "cubismo": "cubismo",
}


DEFAULT_CATEGORIES = (
    ("Barroco", "barroco"),
    ("Cubismo", "cubismo"),
    ("Impresionismo", "impresionismo"),
    ("Expresionismo", "expresionismo"),
    ("Pop Art", "pop-art"),
)


def seed_missing_categories(session: Session) -> None:
    """Create the required dataset categories without changing existing rows."""
    added_categories = False

    for nombre, slug in DEFAULT_CATEGORIES:
        category = session.exec(
            select(Categoria).where(
                or_(
                    Categoria.slug == slug,
                    func.lower(Categoria.nombre) == nombre.lower(),
                )
            )
        ).first()
        if category is None:
            session.add(Categoria(nombre=nombre, slug=slug))
            added_categories = True

    if added_categories:
        session.commit()


def get_categoria_by_slug(session: Session, slug: str) -> Optional[Categoria]:
    return session.exec(select(Categoria).where(Categoria.slug == slug)).first()


def resolve_categoria_id_for_label(session: Session, label: Optional[str]) -> Optional[int]:
    """Resuelve el id de categoría para una etiqueta del CNN usando su slug.

    Devuelve None si la etiqueta no tiene mapeo o la categoría no existe.
    """
    if not label:
        return None
    slug = CNN_LABEL_TO_SLUG.get(label.strip().lower())
    if slug is None:
        logger.warning("CNN label %r has no category mapping; storing image without category", label)
        return None
    categoria = get_categoria_by_slug(session, slug)
    if categoria is None:
        logger.warning("Category with slug %r not found for CNN label %r", slug, label)
        return None
    return categoria.id
