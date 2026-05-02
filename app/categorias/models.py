from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.core.timestamps import created_at_field, updated_at_field


class Categoria(SQLModel, table=True):
    __tablename__ = "categorias"

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=100, nullable=False)
    slug: str = Field(max_length=100, unique=True, nullable=False, index=True)
    descripcion: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()
