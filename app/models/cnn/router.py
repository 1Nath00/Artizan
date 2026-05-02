import uuid

import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from typing import Optional

from app.config import CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET, CLOUDINARY_CLOUD_NAME
from app.models.cnn.model import classify_image

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True,
)

router = APIRouter(prefix="/models/cnn", tags=["CNN - Image Classification"])


class Prediction(BaseModel):
    label: str
    confidence: float


class ClassificationResponse(BaseModel):
    predictions: list[Prediction]
    imagen_url: Optional[str] = None


@router.post("/classify", response_model=ClassificationResponse)
async def classify(
    file: UploadFile = File(...),
    top_k: int = 5,
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

    # Subir a Cloudinary
    imagen_url = None
    if CLOUDINARY_CLOUD_NAME:
        try:
            ext = (file.filename or "image.jpg").rsplit(".", 1)[-1].lower()
            public_id = f"artizan/cnn/{uuid.uuid4().hex}"
            result = cloudinary.uploader.upload(
                image_bytes,
                public_id=public_id,
                overwrite=False,
                resource_type="image",
            )
            imagen_url = result["secure_url"]
        except Exception:
            pass

    return ClassificationResponse(
        predictions=[Prediction(**r) for r in results],
        imagen_url=imagen_url,
    )
