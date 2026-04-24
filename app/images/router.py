from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile, status
from sqlmodel import Session

from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.database import get_session
from app.images import service
from app.middleware import logger as request_logger
from app.images.schemas import ImageResponse

router = APIRouter(prefix="/images", tags=["images"])


@router.post("/upload", response_model=ImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    categoria_id: int | None = Form(default=None),
    titulo: str | None = Form(default=None),
    descripcion: str | None = Form(default=None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    image = await service.save_image(
        session,
        file,
        usuario_id=current_user.id,
        categoria_id=categoria_id,
        titulo=titulo,
        descripcion=descripcion,
    )
    client_host = request.client.host if request.client else "unknown"
    request_logger.info(
        f"Image uploaded id={image.id} titulo={image.titulo} "
        f"by=user:{current_user.id} from={client_host}"
    )
    return image


@router.get("/", response_model=list[ImageResponse])
def list_images(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    return service.list_images(session, usuario_id=current_user.id)


@router.get("/{image_id}", response_model=ImageResponse)
def get_image(
    image_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    image = service.get_image(session, image_id)
    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return image


@router.get("/{image_id}/file")
def download_image(
    image_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    image = service.get_image(session, image_id)
    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    file_path = Path(image.imagen_url)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    ext = file_path.suffix.lstrip(".")
    client_host = request.client.host if request.client else "unknown"
    request_logger.info(f"Image downloaded id={image_id} by=user:{current_user.id} from={client_host}")
    return Response(content=file_path.read_bytes(), media_type=f"image/{ext}")


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(
    image_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    deleted = service.delete_image(session, image_id, usuario_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    client_host = request.client.host if request.client else "unknown"
    request_logger.info(f"Image deleted id={image_id} by=user:{current_user.id} from={client_host}")
