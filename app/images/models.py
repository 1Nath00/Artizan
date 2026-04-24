from datetime import datetime
from typing import Optional

from sqlalchemy import Column, LargeBinary
from sqlmodel import Field, SQLModel


class Image(SQLModel, table=True):
    __tablename__ = "images"

    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str = Field(nullable=False, index=True)
    original_name: str = Field(nullable=False)
    content_type: str = Field(nullable=False)
    size: int = Field(nullable=False)
    uploaded_by: str = Field(nullable=False, index=True)
    content: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
