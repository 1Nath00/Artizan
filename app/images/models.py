from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.core.timestamps import created_at_field, updated_at_field


class Image(SQLModel, table=True):
    __tablename__ = "images"

    id: Optional[int] = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="users.id", nullable=False)
    imagen_url: str = Field(nullable=False)
    categoria_id: Optional[int] = Field(
        default=None,
        foreign_key="categorias.id",
        nullable=True,
    )
    titulo: Optional[str] = Field(default=None, max_length=255, nullable=True)
    descripcion: Optional[str] = Field(default=None, nullable=True)
    estado: str = Field(default="pendiente", max_length=20, nullable=False)
    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()
