import uuid
from fastapi import HTTPException, UploadFile, status
from sqlmodel import Session, select

from app.config import ALLOWED_EXTENSIONS, MAX_IMAGE_SIZE_MB
from app.images.models import Image

MAX_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024


def _get_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _to_record(image: Image, include_content: bool = False) -> dict:
    record = {
        "id": image.id,
        "filename": image.filename,
        "original_name": image.original_name,
        "content_type": image.content_type,
        "size": image.size,
        "uploaded_by": image.uploaded_by,
    }
    if include_content:
        record["content"] = image.content
    return record


async def save_image(session: Session, file: UploadFile, username: str) -> dict:

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

    unique_name = f"{uuid.uuid4().hex}.{ext}"

    image = Image(
        filename=unique_name,
        original_name=file.filename or unique_name,
        content_type=file.content_type or f"image/{ext}",
        size=len(content),
        uploaded_by=username,
        content=content,
    )
    session.add(image)
    session.commit()
    session.refresh(image)
    return _to_record(image)


def list_images(session: Session, username: str | None = None) -> list[dict]:
    statement = select(Image)
    if username:
        statement = statement.where(Image.uploaded_by == username)
    images = session.exec(statement).all()
    return [_to_record(image) for image in images]


def get_image(session: Session, image_id: int, include_content: bool = False) -> dict | None:
    image = session.get(Image, image_id)
    if not image:
        return None
    return _to_record(image, include_content=include_content)


def delete_image(session: Session, image_id: int, username: str) -> bool:
    image = session.get(Image, image_id)
    if not image:
        return False
    if image.uploaded_by != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this image",
        )
    session.delete(image)
    session.commit()
    return True
