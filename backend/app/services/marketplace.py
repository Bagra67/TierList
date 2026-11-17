import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.exceptions.templates import TemplateNotFoundError
from app.models.template import Template
from app.repositories import templates as template_repository


@dataclass(frozen=True)
class PublicTemplate:
    template: Template
    owner_name: str


class MarketplaceService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_template(self, template_id: uuid.UUID) -> PublicTemplate:
        listed: tuple[Template, str] | None = (
            template_repository.get_listed_template_with_owner_name(
                self._session, template_id, datetime.now(UTC)
            )
        )
        if listed is None:
            raise TemplateNotFoundError
        template, owner_name = listed
        return PublicTemplate(template, owner_name)
