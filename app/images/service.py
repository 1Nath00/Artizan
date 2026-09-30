import logging
import uuid
from pathlib import Path

import cloudinary
import cloudinary.uploader
from ultralytics import YOLO
import httpx
from PIL import Image as PILImage
import io
from fastapi import HTTPException, UploadFile, status
from sqlmodel import Session, select

from app.config import (
    ALLOWED_EXTENSIONS,
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    CLOUDINARY_CLOUD_NAME,
    MAX_IMAGE_SIZE_MB,
)
from app.images.models import Image

MAX_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024
UPLOADS_DIR = Path("uploads")

logger = logging.getLogger(__name__)

model: YOLO = YOLO("yolo11n.pt")

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True,
)


def _get_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


async def save_image(
    session: Session,
    file: UploadFile,
    usuario_id: int,
    categoria_id: int | None = None,
    titulo: str | None = None,
    descripcion: str | None = None,
) -> Image:
    ext = _get_extension(file.filename or "")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_IMAGE_SIZE_MB} MB",
        )

    UPLOADS_DIR.mkdir(exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = UPLOADS_DIR / unique_name
    file_path.write_bytes(content)

    # Subir a Cloudinary
    cloudinary_url = str(file_path)
    if CLOUDINARY_CLOUD_NAME:
        try:
            result = cloudinary.uploader.upload(
                str(file_path),
                public_id=f"artizan/images/{unique_name.rsplit('.', 1)[0]}",
                overwrite=False,
                resource_type="image",
            )
            cloudinary_url = result["secure_url"]
            file_path.unlink(missing_ok=True)  # ya no se necesita la copia local
        except Exception:
            logger.exception("Cloudinary upload failed, falling back to local path")
    else:
        logger.warning("CLOUDINARY_CLOUD_NAME is not set, skipping Cloudinary upload")

    image = Image(
        usuario_id=usuario_id,
        imagen_url=cloudinary_url,
        categoria_id=categoria_id,
        titulo=titulo,
        descripcion=descripcion,
    )
    session.add(image)
    session.commit()
    session.refresh(image)
    return image


def list_images(session: Session, usuario_id: int | None = None) -> list[Image]:
    statement = select(Image)
    if usuario_id is not None:
        statement = statement.where(Image.usuario_id == usuario_id)
    return list(session.exec(statement).all())


def get_image(session: Session, image_id: int) -> Image | None:
    return session.get(Image, image_id)


def delete_image(session: Session, image_id: int, usuario_id: int) -> bool:
    image = session.get(Image, image_id)
    if not image:
        return False
    if image.usuario_id != usuario_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this image",
        )
    # Remove file from disk if it exists
    file_path = Path(image.imagen_url)
    if file_path.exists():
        file_path.unlink()

    session.delete(image)
    session.commit()
    return True

def detect_objects(image_url: str, conf: float = 0.25) -> list[dict]:
    response = httpx.get(image_url, timeout=10.0, follow_redirects=True)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if not content_type.startswith("image/"):
        raise ValueError(f"La URL no devolvió una imagen válida (content-type={content_type})")

    img = PILImage.open(io.BytesIO(response.content)).convert("RGB")
    results = model(img, conf=conf)
    detections = []
    for r in results:
        for box in r.boxes:
            detections.append({
                "clase": model.names[int(box.cls)],
                "confianza": round(float(box.conf), 4),
                "bbox": [round(x, 2) for x in box.xyxy.tolist()[0]],
            })
    return detections