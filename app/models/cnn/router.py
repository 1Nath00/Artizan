from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.models.cnn.model import classify_image

router = APIRouter(prefix="/models/cnn", tags=["CNN - Image Classification"])


class Prediction(BaseModel):
    label: str
    confidence: float


class ClassificationResponse(BaseModel):
    predictions: list[Prediction]


@router.post("/classify", response_model=ClassificationResponse)
async def classify(
    file: UploadFile = File(...),
    top_k: int = 5,
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

    return ClassificationResponse(predictions=[Prediction(**r) for r in results])
