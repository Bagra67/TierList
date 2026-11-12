import uuid

from pydantic import BaseModel


class ImageUploadResponse(BaseModel):
    """Image envoyée et compressée : son id, à mettre dans une tuile, son adresse publique et ses
    dimensions en pixels."""

    id: uuid.UUID
    url: str
    width: int
    height: int
