from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ImageResponse(BaseModel):
    id: int
    usuario_id: int
    imagen_url: str
    categoria_id: Optional[int]
    titulo: Optional[str]
    descripcion: Optional[str]
    estado: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ImageCreate(BaseModel):
    imagen_url: str
    categoria_id: Optional[int] = None
    titulo: Optional[str] = None
    descripcion: Optional[str] = None


class Prediction(BaseModel):
    label: str
    confidence: float


class Detection(BaseModel):
    clase: str
    confianza: float
    bbox: list[float]


class AnalyzeResponse(BaseModel):
    image_id: int
    imagen_url: str
    predictions: list[Prediction]
    detections: list[Detection]

