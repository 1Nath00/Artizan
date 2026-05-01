from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.database import get_session
from app.pinturas.models import Pintura

router = APIRouter(prefix="/pinturas", tags=["pinturas"])


@router.get("/", response_model=List[Pintura])
def list_pinturas(
    categoria: Optional[str] = Query(None, description="Baroque o Cubism"),
    autor: Optional[str] = Query(None, description="Filtrar por autor"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
):
    query = select(Pintura)
    if categoria:
        query = query.where(Pintura.categoria == categoria)
    if autor:
        query = query.where(Pintura.autor.ilike(f"%{autor}%"))
    query = query.offset(skip).limit(limit)
    return session.exec(query).all()


@router.get("/categoria/{categoria}", response_model=List[Pintura])
def list_pinturas_por_categoria(
    categoria: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
):
    """Obtener todas las pinturas de una categoría (Baroque o Cubism)."""
    query = (
        select(Pintura)
        .where(Pintura.categoria == categoria)
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


@router.get("/", response_model=List[Pintura])
def list_pinturas(
    categoria: Optional[str] = Query(None, description="Baroque o Cubism"),
    autor: Optional[str] = Query(None, description="Filtrar por autor"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
):
    query = select(Pintura)
    if categoria:
        query = query.where(Pintura.categoria == categoria)
    if autor:
        query = query.where(Pintura.autor.ilike(f"%{autor}%"))
    query = query.offset(skip).limit(limit)
    return session.exec(query).all()


@router.get("/{pintura_id}", response_model=Pintura)
def get_pintura(pintura_id: int, session: Session = Depends(get_session)):
    pintura = session.get(Pintura, pintura_id)
    if not pintura:
        raise HTTPException(status_code=404, detail="Pintura no encontrada")
    return pintura
