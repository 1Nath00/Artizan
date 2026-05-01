from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Pintura(SQLModel, table=True):
    __tablename__ = "pinturas"

    id: Optional[int] = Field(default=None, primary_key=True)
    autor: str = Field(nullable=False, index=True)
    nombre: str = Field(nullable=False)
    año: Optional[int] = Field(default=None, nullable=True)
    categoria: str = Field(nullable=False, index=True)  # "Baroque" o "Cubism"
    url_imagen: str = Field(nullable=False)
    filename_original: str = Field(nullable=False, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
