import uuid

import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from typing import Optional
from sqlmodel import Session, select

from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.categorias.models import Categoria
from app.config import CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET, CLOUDINARY_CLOUD_NAME
from app.database import get_session
from app.images.models import Image
from app.models.cnn.model import classify_image

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True,
)

router = APIRouter(prefix="/models/cnn", tags=["CNN - Image Classification"])

# Map model output labels → categoria slug in DB
_LABEL_TO_SLUG: dict[str, str] = {
    "barroco": "baroque",
    "cubismo": "cubism",
}


class Prediction(BaseModel):
    label: str
    confidence: float


class ClassificationResponse(BaseModel):
    predictions: list[Prediction]
    imagen_url: Optional[str] = None
    imagen_id: Optional[int] = None
    categoria: Optional[str] = None


@router.post("/classify", response_model=ClassificationResponse)
async def classify(
    file: UploadFile = File(...),
    top_k: int = 5,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Upload an image and receive the top-k classification predictions using
    a pre-trained CNN. The result is saved to the database linked to the
    authenticated user.
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

    # Resolver categoria a partir de la predicción principal
    top_label: str = results[0]["label"] if results else ""
    slug = _LABEL_TO_SLUG.get(top_label.lower())
    categoria_id: Optional[int] = None
    categoria_nombre: Optional[str] = None
    if slug:
        categoria = session.exec(
            select(Categoria).where(Categoria.slug == slug)
        ).first()
        if categoria:
            categoria_id = categoria.id
            categoria_nombre = categoria.nombre

    # Guardar en la tabla images
    imagen_db = Image(
        usuario_id=current_user.id,
        imagen_url=imagen_url or "",
        categoria_id=categoria_id,
        titulo=file.filename or "sin_nombre",
        descripcion=f"CNN classify – top: {top_label} ({results[0]['confidence']:.2%})" if results else None,
    )
    session.add(imagen_db)
    session.commit()
    session.refresh(imagen_db)

    return ClassificationResponse(
        predictions=[Prediction(**r) for r in results],
        imagen_url=imagen_url,
        imagen_id=imagen_db.id,
        categoria=categoria_nombre,
    )
