import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.exceptions.templates import TemplateNotFoundError
from app.models.template import Template
from app.models.user import User
from app.repositories import templates as template_repository
from app.repositories import users as user_repository


@dataclass(frozen=True)
class PublicTemplate:
    template: Template
    owner_name: str


class MarketplaceService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_template(self, template_id: uuid.UUID) -> PublicTemplate:
        template: Template | None = template_repository.get_listed_template(
            self._session, template_id, datetime.now(UTC)
        )
        if template is None:
            raise TemplateNotFoundError
        owner: User | None = user_repository.get_user_by_id(self._session, template.owner_id)
        if owner is None:
            raise TemplateNotFoundError
        return PublicTemplate(template, owner.display_name)
