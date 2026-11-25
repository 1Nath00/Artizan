from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel

from app.categorias.models import Categoria


class Pintura(SQLModel, table=True):
    __tablename__ = "pinturas"

    id: Optional[int] = Field(default=None, primary_key=True)
    autor: str = Field(nullable=False, index=True)
    nombre: str = Field(nullable=False)
    año: Optional[int] = Field(default=None, nullable=True)
    categoria_id: int = Field(foreign_key="categorias.id", index=True)
    categoria: Categoria = Relationship()
    url_imagen: str = Field(nullable=False)
    filename_original: str = Field(nullable=False, unique=True)
    descripcion: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
