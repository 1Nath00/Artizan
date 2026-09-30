import logging
import uuid
from pathlib import Path

import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from typing import Optional
from sqlmodel import Session

from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.config import CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET, CLOUDINARY_CLOUD_NAME
from app.database import get_session
from app.images.models import Image
from app.models.cnn.model import classify_image

UPLOADS_DIR = Path("uploads")

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True,
)

router = APIRouter(prefix="/models/cnn", tags=["CNN - Image Classification"])

logger = logging.getLogger(__name__)


class Prediction(BaseModel):
    label: str
    confidence: float


class ClassificationResponse(BaseModel):
    predictions: list[Prediction]
    imagen_url: Optional[str] = None
    image_id: Optional[int] = None


@router.post("/classify", response_model=ClassificationResponse)
async def classify(
    file: UploadFile = File(...),
    top_k: int = 5,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Upload an image and receive the top-k classification predictions using
    a pre-trained ResNet-50 CNN.
    """
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image files are accepted",
        )
    if top_k < 1 or top_k > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="top_k must be between 1 and 100",
        )

    image_bytes = await file.read()
    try:
        results = classify_image(image_bytes, top_k=top_k)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not process image: {exc}",
        ) from exc

    # Subir a Cloudinary; si no está configurado o falla, se guarda localmente
    ext = (file.filename or "image.jpg").rsplit(".", 1)[-1].lower()
    UPLOADS_DIR.mkdir(exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = UPLOADS_DIR / unique_name
    file_path.write_bytes(image_bytes)
    imagen_url = str(file_path)

    if CLOUDINARY_CLOUD_NAME:
        try:
            public_id = f"artizan/cnn/{uuid.uuid4().hex}"
            result = cloudinary.uploader.upload(
                image_bytes,
                public_id=public_id,
                overwrite=False,
                resource_type="image",
            )
            imagen_url = result["secure_url"]
            file_path.unlink(missing_ok=True)  # ya no se necesita la copia local
        except Exception:
            logger.exception("Cloudinary upload failed, falling back to local path")
    else:
        logger.warning("CLOUDINARY_CLOUD_NAME is not set, skipping Cloudinary upload")

    top_prediction = results[0]["label"] if results else None
    image = Image(
        usuario_id=current_user.id,
        imagen_url=imagen_url,
        titulo=top_prediction,
        estado="clasificada",
    )
    session.add(image)
    session.commit()
    session.refresh(image)
    image_id = image.id

    return ClassificationResponse(
        predictions=[Prediction(**r) for r in results],
        imagen_url=imagen_url,
        image_id=image_id,
    )
