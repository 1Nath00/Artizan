from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlmodel import Session, select

from app.categorias.models import Categoria
from app.categorias.service import get_categoria_by_slug
from app.database import get_session
from app.pinturas.models import Pintura

router = APIRouter(prefix="/pinturas", tags=["pinturas"])


@router.get("/", response_model=List[Pintura])
def list_pinturas(
    categoria_id: Optional[int] = Query(None, ge=1, description="ID de la categoría"),
    autor: Optional[str] = Query(None, description="Filtrar por nombre de autor"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
):
    query = select(Pintura)
    if categoria_id is not None:
        query = query.where(Pintura.categoria_id == categoria_id)
    if autor:
        query = query.where(Pintura.autor.ilike(f"%{autor}%"))
    query = query.offset(skip).limit(limit)
    return session.exec(query).all()


@router.get("/search", response_model=List[Pintura])
def search_pinturas(
    q: str = Query(..., min_length=1, max_length=100, description="Texto a buscar"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
):
    pattern = f"%{q.strip()}%"
    if not q.strip():
        return []

    query = (
        select(Pintura)
        .join(Categoria, Categoria.id == Pintura.categoria_id)
        .where(
            or_(
                Pintura.nombre.ilike(pattern),
                Pintura.autor.ilike(pattern),
                Pintura.filename_original.ilike(pattern),
                Categoria.nombre.ilike(pattern),
                Categoria.slug.ilike(pattern),
            )
        )
        .offset(skip)
        .limit(limit)
    )
    return session.exec(query).all()


@router.get("/categoria/{slug}", response_model=List[Pintura])
def list_pinturas_by_categoria_slug(
    slug: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
):
    categoria = get_categoria_by_slug(session, slug)
    if categoria is None:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    query = (
        select(Pintura)
        .where(Pintura.categoria_id == categoria.id)
        .offset(skip)
        .limit(limit)
    )
    return session.exec(query).all()


@router.get("/{pintura_id}", response_model=Pintura)
def get_pintura(pintura_id: int, session: Session = Depends(get_session)):
    pintura = session.get(Pintura, pintura_id)
    if not pintura:
        raise HTTPException(status_code=404, detail="Pintura no encontrada")
    return pintura
