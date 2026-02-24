from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, status
from fastapi.responses import FileResponse

from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.images import service
from app.images.schemas import ImageResponse

router = APIRouter(prefix="/images", tags=["images"])


def _build_response(record: dict, request: Request) -> ImageResponse:
    base_url = str(request.base_url).rstrip("/")
    return ImageResponse(
        id=record["id"],
        filename=record["filename"],
        original_name=record["original_name"],
        content_type=record["content_type"],
        size=record["size"],
        uploaded_by=record["uploaded_by"],
        url=f"{base_url}/images/{record['id']}/file",
    )


@router.post("/upload", response_model=ImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
):
    record = await service.save_image(file, current_user.username)
    return _build_response(record, request)


@router.get("/", response_model=list[ImageResponse])
def list_images(request: Request, current_user: User = Depends(get_current_active_user)):
    records = service.list_images(username=current_user.username)
    return [_build_response(r, request) for r in records]


@router.get("/{image_id}", response_model=ImageResponse)
def get_image(
    image_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    record = service.get_image(image_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return _build_response(record, request)


@router.get("/{image_id}/file")
def download_image(image_id: int, current_user: User = Depends(get_current_active_user)):
    record = service.get_image(image_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return FileResponse(record["path"], media_type=record["content_type"])


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(image_id: int, current_user: User = Depends(get_current_active_user)):
    deleted = service.delete_image(image_id, current_user.username)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
