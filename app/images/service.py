import os
import uuid
from pathlib import Path

import aiofiles
from fastapi import HTTPException, UploadFile, status

from app.config import ALLOWED_EXTENSIONS, MAX_IMAGE_SIZE_MB, UPLOAD_DIR

MAX_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024

# In-memory store (replace with a database in production)
_image_store: dict[int, dict] = {}
_next_id: int = 1


def _get_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _ensure_upload_dir() -> Path:
    path = Path(UPLOAD_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


async def save_image(file: UploadFile, username: str) -> dict:
    global _next_id

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

    upload_dir = _ensure_upload_dir()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = upload_dir / unique_name

    async with aiofiles.open(file_path, "wb") as out_file:
        await out_file.write(content)

    image_id = _next_id
    _next_id += 1
    record = {
        "id": image_id,
        "filename": unique_name,
        "original_name": file.filename or unique_name,
        "content_type": file.content_type or f"image/{ext}",
        "size": len(content),
        "uploaded_by": username,
        "path": str(file_path),
    }
    _image_store[image_id] = record
    return record


def list_images(username: str | None = None) -> list[dict]:
    records = list(_image_store.values())
    if username:
        records = [r for r in records if r["uploaded_by"] == username]
    return records


def get_image(image_id: int) -> dict | None:
    return _image_store.get(image_id)


def delete_image(image_id: int, username: str) -> bool:
    record = _image_store.get(image_id)
    if not record:
        return False
    if record["uploaded_by"] != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this image",
        )
    path = Path(record["path"])
    if path.exists():
        os.remove(path)
    del _image_store[image_id]
    return True
