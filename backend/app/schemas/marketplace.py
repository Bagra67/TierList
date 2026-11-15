import uuid

from pydantic import BaseModel

from app.schemas.templates import TierResponse


class PublicTileResponse(BaseModel):
    """A tile of a public template, in the template's order. `image_removed` is true when moderation
    hid or deleted the image: `image_url` is then null."""

    id: uuid.UUID
    text: str | None
    image_url: str | None
    image_removed: bool


class PublicTemplateResponse(BaseModel):
    """A public template as everyone sees it: its name, its owner's display name, its tags, its
    tiers and its tiles in their order."""

    id: uuid.UUID
    name: str
    owner_name: str
    tags: list[str]
    tiers: list[TierResponse]
    tiles: list[PublicTileResponse]
