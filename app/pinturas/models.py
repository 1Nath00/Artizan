from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.core.timestamps import created_at_field, updated_at_field


class Pintura(SQLModel, table=True):
    __tablename__ = "pinturas"

    id: Optional[int] = Field(default=None, primary_key=True)
    titulo: str = Field(max_length=255, nullable=False)
    artista: Optional[str] = Field(default=None, max_length=255, nullable=True)
    anio: Optional[int] = Field(default=None, nullable=True)
    descripcion: Optional[str] = Field(default=None, nullable=True)
    categoria_id: Optional[int] = Field(
        default=None,
        foreign_key="categorias.id",
        nullable=True,
    )

    imagen_url: str = Field(nullable=False)
    imagen_thumb: Optional[str] = Field(default=None, nullable=True)

    destacada: bool = Field(default=False)
    activa: bool = Field(default=True)
    orden: int = Field(default=0)

    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()
