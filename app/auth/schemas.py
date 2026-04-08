from datetime import datetime
from typing import Optional

from pydantic import EmailStr, field_validator
from sqlmodel import SQLModel


class UserBase(SQLModel):
    """Campos base compartidos entre User schemas."""
    username: str
    email: EmailStr


class UserCreate(UserBase):
    """Schema para crear un usuario."""
    password: str
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validar que la contraseña no exceda el límite de bcrypt (72 bytes)."""
        if not v:
            raise ValueError('Password cannot be empty')
        
        password_bytes = v.encode('utf-8')
        if len(password_bytes) > 72:
            raise ValueError(
                f'Password is too long ({len(password_bytes)} bytes). '
                f'Maximum length is 72 bytes. Please use a shorter password.'
            )
        
        if len(v) < 4:
            raise ValueError('Password must be at least 4 characters long')
        
        return v


class UserResponse(UserBase):
    """Schema para respuestas de usuario."""
    id: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(SQLModel):
    """Schema para la petición de login - solo username y password."""
    username: str
    password: str


class Token(SQLModel):
    """Schema para el token de acceso."""
    access_token: str
    token_type: str


class TokenData(SQLModel):
    """Schema para los datos del token."""
    username: Optional[str] = None
