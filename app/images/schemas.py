from pydantic import BaseModel


class ImageResponse(BaseModel):
    id: int
    filename: str
    original_name: str
    content_type: str
    size: int
    uploaded_by: str
    url: str

    model_config = {"from_attributes": True}
