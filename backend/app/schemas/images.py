import uuid

from pydantic import BaseModel


class ImageUploadResponse(BaseModel):
    id: uuid.UUID
    # Adresse publique de l'image compressée (WebP), lisible sans authentification
    url: str
    width: int
    height: int
