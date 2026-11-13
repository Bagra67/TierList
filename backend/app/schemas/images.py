import uuid

from pydantic import BaseModel


class ImageUploadResponse(BaseModel):
    """Uploaded and compressed image: its id, to put in a tile, its public address and its
    dimensions in pixels."""

    id: uuid.UUID
    url: str
    width: int
    height: int
