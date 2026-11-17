from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.categorias.models import Categoria


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
