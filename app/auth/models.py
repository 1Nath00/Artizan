from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.core.timestamps import created_at_field, updated_at_field


class User(SQLModel, table=True):
    """Modelo de usuario en la base de datos."""
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, nullable=False)
    email: str = Field(unique=True, index=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    is_active: bool = Field(default=True)
    created_at: datetime = created_at_field()
    updated_at: datetime = updated_at_field()
