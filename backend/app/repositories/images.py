from sqlalchemy.orm import Session

from app.models.image import Image


def add_image(session: Session, image: Image) -> None:
    session.add(image)
