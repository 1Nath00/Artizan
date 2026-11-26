from typing import Literal

from pydantic import BaseModel, Field

from app.config import MAX_IMAGE_SIZE_MB

ALLOWED_IDENTIFICATION_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


class IdentificarImagenRequest(BaseModel):
    """Datos del archivo validados antes de ejecutar la inferencia."""

    content_type: Literal["image/jpeg", "image/png", "image/webp"]
    tamano_bytes: int = Field(gt=0, le=MAX_IMAGE_SIZE_MB * 1024 * 1024)


class PinturaIdentificada(BaseModel):
    """Datos públicos de una pintura recuperada del índice."""

    id: int
    imagen_url: str
    autor: str
    anio: int | None
    descripcion: str | None
    categoria_id: int


class CandidatoPintura(PinturaIdentificada):
    """Candidato recuperado con su similitud coseno."""

    score: float


class IdentificarImagenResponse(BaseModel):
    """Respuesta estable del endpoint de identificación."""

    estado: Literal["encontrada", "dudosa", "no_encontrada"]
    score: float
    pintura: PinturaIdentificada | None
    candidatos: list[CandidatoPintura]
