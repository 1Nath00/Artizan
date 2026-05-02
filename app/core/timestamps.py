from datetime import datetime

from sqlalchemy import Column, DateTime
from sqlmodel import Field


def created_at_field() -> datetime:
    """Campo created_at: se guarda automáticamente al crear el registro."""
    return Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            "created_at",
            DateTime,
            default=datetime.utcnow,
            nullable=False,
        ),
    )


def updated_at_field() -> datetime:
    """Campo updated_at: se guarda al crear y se actualiza automáticamente en cada UPDATE."""
    return Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            "updated_at",
            DateTime,
            default=datetime.utcnow,
            onupdate=datetime.utcnow,
            nullable=False,
        ),
    )
