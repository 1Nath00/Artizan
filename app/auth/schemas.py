from datetime import datetime
from typing import Optional

from pydantic import EmailStr
from sqlmodel import SQLModel


class UserBase(SQLModel):
    """Campos base compartidos entre User schemas."""
    username: str
    email: EmailStr


class UserCreate(UserBase):
    """Schema para crear un usuario."""
    password: str


class UserResponse(UserBase):
    """Schema para respuestas de usuario."""
    id: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(SQLModel):
    """Schema para el token de acceso."""
    access_token: str
    token_type: str


class TokenData(SQLModel):
    """Schema para los datos del token."""
    username: Optional[str] = None
