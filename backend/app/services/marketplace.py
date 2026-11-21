import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.constants.marketplace import MARKETPLACE_POPULAR_TAG_COUNT, MarketplaceSort
from app.constants.templates import FEATURED_TEMPLATES_MAX
from app.core.cursor import decode_cursor, encode_cursor, split_page
from app.core.search_query import build_search_query
from app.core.search_text import normalize_search_text
from app.exceptions.auth import EmailNotVerifiedError
from app.exceptions.templates import (
    CannotFavoriteOwnTemplateError,
    CannotLikeOwnTemplateError,
    TemplateNotFoundError,
)
from app.models.template import Template
from app.models.tile import Tile
from app.models.user import User
from app.repositories import template_favorites as favorite_repository
from app.repositories import template_likes as like_repository
from app.repositories import templates as template_repository


@dataclass(frozen=True)
class PublicTemplate:
    template: Template
    owner_name: str
    like_count: int


@dataclass(frozen=True)
class MarketplaceTemplate:
    template: Template
    owner_name: str
    like_count: int
    tile_count: int
    first_tile: Tile | None


@dataclass(frozen=True)
class MarketplacePage:
    items: list[MarketplaceTemplate]
    next_cursor: str | None


class PopularPosition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sort: Literal[MarketplaceSort.POPULAR]
    like_count: int
    first_made_public_at: datetime
    id: uuid.UUID


class NewestPosition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sort: Literal[MarketplaceSort.NEWEST]
    first_made_public_at: datetime
    id: uuid.UUID


@dataclass(frozen=True)
class LikeState:
    liked: bool
    like_count: int
    can_like: bool


@dataclass(frozen=True)
class TemplateLikeState(LikeState):
    template_id: uuid.UUID


class FavoritesPosition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    favorited_at: datetime
    id: uuid.UUID


@dataclass(frozen=True)
class FavoriteState:
    favorited: bool
    can_favorite: bool


@dataclass(frozen=True)
class TemplateFavoriteState(FavoriteState):
    template_id: uuid.UUID


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
        like_count: int = like_repository.count_likes(self._session, template.id)
        return PublicTemplate(template, owner_name, like_count)

    def like_state(self, user: User, template_id: uuid.UUID) -> LikeState:
        owner_id: uuid.UUID = self._listed_owner_id(template_id)
        liked: bool = like_repository.has_liked(self._session, template_id, user.id)
        return self._like_state(user, template_id, owner_id, liked)

    def like(self, user: User, template_id: uuid.UUID) -> LikeState:
        owner_id: uuid.UUID = self._listed_owner_id(template_id)
        if owner_id == user.id:
            raise CannotLikeOwnTemplateError
        if not user.email_verified:
            raise EmailNotVerifiedError
        like_repository.add_like(self._session, template_id, user.id)
        self._session.commit()
        return self._like_state(user, template_id, owner_id, liked=True)

    def unlike(self, user: User, template_id: uuid.UUID) -> LikeState:
        owner_id: uuid.UUID = self._listed_owner_id(template_id)
        like_repository.remove_like(self._session, template_id, user.id)
        self._session.commit()
        return self._like_state(user, template_id, owner_id, liked=False)

    def like_states(self, user: User, template_ids: list[uuid.UUID]) -> list[TemplateLikeState]:
        unique_ids: list[uuid.UUID] = list(dict.fromkeys(template_ids))
        owner_ids: dict[uuid.UUID, uuid.UUID] = template_repository.list_listed_template_owner_ids(
            self._session, unique_ids, datetime.now(UTC)
        )
        listed_ids: list[uuid.UUID] = [
            template_id for template_id in unique_ids if template_id in owner_ids
        ]
        like_counts: dict[uuid.UUID, int] = like_repository.count_likes_of_templates(
            self._session, listed_ids
        )
        liked_ids: set[uuid.UUID] = like_repository.list_liked_template_ids(
            self._session, user.id, listed_ids
        )
        return [
            TemplateLikeState(
                liked=template_id in liked_ids,
                like_count=like_counts.get(template_id, 0),
                can_like=_is_not_owner(user, owner_ids[template_id]),
                template_id=template_id,
            )
            for template_id in listed_ids
        ]

    def favorite_state(self, user: User, template_id: uuid.UUID) -> FavoriteState:
        owner_id: uuid.UUID = self._listed_owner_id(template_id)
        favorited: bool = favorite_repository.has_favorited(self._session, template_id, user.id)
        return FavoriteState(favorited=favorited, can_favorite=_is_not_owner(user, owner_id))

    def favorite(self, user: User, template_id: uuid.UUID) -> FavoriteState:
        owner_id: uuid.UUID = self._listed_owner_id(template_id)
        if owner_id == user.id:
            raise CannotFavoriteOwnTemplateError
        if not user.email_verified:
            raise EmailNotVerifiedError
        favorite_repository.add_favorite(self._session, template_id, user.id)
        self._session.commit()
        return FavoriteState(favorited=True, can_favorite=True)

    def unfavorite(self, user: User, template_id: uuid.UUID) -> FavoriteState:
        owner_id: uuid.UUID = self._listed_owner_id(template_id)
        favorite_repository.remove_favorite(self._session, template_id, user.id)
        self._session.commit()
        return FavoriteState(favorited=False, can_favorite=_is_not_owner(user, owner_id))

    def favorite_states(
        self, user: User, template_ids: list[uuid.UUID]
    ) -> list[TemplateFavoriteState]:
        unique_ids: list[uuid.UUID] = list(dict.fromkeys(template_ids))
        owner_ids: dict[uuid.UUID, uuid.UUID] = template_repository.list_listed_template_owner_ids(
            self._session, unique_ids, datetime.now(UTC)
        )
        listed_ids: list[uuid.UUID] = [
            template_id for template_id in unique_ids if template_id in owner_ids
        ]
        favorited_ids: set[uuid.UUID] = favorite_repository.list_favorited_template_ids(
            self._session, user.id, listed_ids
        )
        return [
            TemplateFavoriteState(
                favorited=template_id in favorited_ids,
                can_favorite=_is_not_owner(user, owner_ids[template_id]),
                template_id=template_id,
            )
            for template_id in listed_ids
        ]

    def list_favorites(self, user: User, cursor: str | None, limit: int) -> MarketplacePage:
        after: template_repository.FavoritesAfter | None = None
        if cursor is not None:
            position: FavoritesPosition = decode_cursor(cursor, FavoritesPosition)
            after = template_repository.FavoritesAfter(position.favorited_at, position.id)
        rows: list[tuple[Template, str, int, datetime]] = (
            template_repository.list_favorite_templates(
                self._session, datetime.now(UTC), user.id, after, limit + 1
            )
        )
        page_rows, last_row = split_page(rows, limit)
        next_cursor: str | None = (
            None
            if last_row is None
            else encode_cursor(FavoritesPosition(favorited_at=last_row[3], id=last_row[0].id))
        )
        cards: list[MarketplaceTemplate] = self._cards(
            [(template, owner_name, likes) for template, owner_name, likes, _ in page_rows]
        )
        return MarketplacePage(items=cards, next_cursor=next_cursor)

    def list_templates(
        self,
        search: str | None,
        tag: str | None,
        sort: MarketplaceSort,
        cursor: str | None,
        limit: int,
    ) -> MarketplacePage:
        rows: list[tuple[Template, str, int]] = template_repository.list_marketplace_templates(
            self._session,
            datetime.now(UTC),
            search_query=None if search is None else build_search_query(search),
            normalized_tag=None if tag is None else normalize_search_text(tag) or None,
            sort=sort,
            after=None if cursor is None else _after(cursor, sort),
            limit=limit + 1,
        )
        page_rows, last_row = split_page(rows, limit)
        next_cursor: str | None = (
            None if last_row is None else _cursor_after(last_row[0], last_row[2], sort)
        )
        return MarketplacePage(items=self._cards(page_rows), next_cursor=next_cursor)

    def list_featured(self) -> list[MarketplaceTemplate]:
        return self._cards(
            template_repository.list_featured_templates(
                self._session, datetime.now(UTC), FEATURED_TEMPLATES_MAX
            )
        )

    def _cards(self, rows: list[tuple[Template, str, int]]) -> list[MarketplaceTemplate]:
        template_ids: list[uuid.UUID] = [template.id for template, _, _ in rows]
        tile_counts: dict[uuid.UUID, int] = template_repository.count_tiles_of_templates(
            self._session, template_ids
        )
        first_tiles: dict[uuid.UUID, Tile] = template_repository.list_first_tiles_of_templates(
            self._session, template_ids
        )
        return [
            MarketplaceTemplate(
                template,
                owner_name,
                like_count,
                tile_counts.get(template.id, 0),
                first_tiles.get(template.id),
            )
            for template, owner_name, like_count in rows
        ]

    def list_popular_tags(self) -> list[str]:
        return template_repository.list_popular_listed_tags(
            self._session, datetime.now(UTC), MARKETPLACE_POPULAR_TAG_COUNT
        )

    def list_template_updates(self, limit: int) -> list[tuple[uuid.UUID, datetime]]:
        return template_repository.list_listed_template_updates(
            self._session, datetime.now(UTC), limit
        )

    def _listed_owner_id(self, template_id: uuid.UUID) -> uuid.UUID:
        listed: tuple[str, uuid.UUID] | None = (
            template_repository.get_listed_template_name_and_owner(
                self._session, template_id, datetime.now(UTC)
            )
        )
        if listed is None:
            raise TemplateNotFoundError
        return listed[1]

    def _like_state(
        self, user: User, template_id: uuid.UUID, owner_id: uuid.UUID, liked: bool
    ) -> LikeState:
        return LikeState(
            liked=liked,
            like_count=like_repository.count_likes(self._session, template_id),
            can_like=_is_not_owner(user, owner_id),
        )


def _is_not_owner(user: User, owner_id: uuid.UUID) -> bool:
    return owner_id != user.id


def _after(cursor: str, sort: MarketplaceSort) -> template_repository.MarketplaceAfter:
    if sort == MarketplaceSort.POPULAR:
        popular: PopularPosition = decode_cursor(cursor, PopularPosition)
        return template_repository.MarketplaceAfter(
            popular.like_count, popular.first_made_public_at, popular.id
        )
    newest: NewestPosition = decode_cursor(cursor, NewestPosition)
    return template_repository.MarketplaceAfter(None, newest.first_made_public_at, newest.id)


def _cursor_after(last: Template, like_count: int, sort: MarketplaceSort) -> str:
    first_made_public_at: datetime | None = last.first_made_public_at
    if first_made_public_at is None:
        raise RuntimeError("A listed template has a first publication date")
    if sort == MarketplaceSort.POPULAR:
        return encode_cursor(
            PopularPosition(
                sort=MarketplaceSort.POPULAR,
                like_count=like_count,
                first_made_public_at=first_made_public_at,
                id=last.id,
            )
        )
    return encode_cursor(
        NewestPosition(
            sort=MarketplaceSort.NEWEST,
            first_made_public_at=first_made_public_at,
            id=last.id,
        )
    )
