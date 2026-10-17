import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Cookie, Depends, Response

from app.api.dependencies import (
    get_current_user,
    get_game_service,
    get_image_storage,
    get_room_service,
    get_room_viewer,
)
from app.api.responses import UNAUTHORIZED_RESPONSE
from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.constants.rooms import GUEST_COOKIE
from app.core.config import Settings, get_settings
from app.core.errors import ErrorResponse
from app.exceptions.games import GameInProgressError, NoPlacingParticipantError
from app.exceptions.http import AppHTTPException
from app.exceptions.rooms import (
    BanNotFoundError,
    CannotRemoveRoomAdminError,
    GuestLinkInvalidError,
    NicknameTakenError,
    ParticipantNotFoundError,
    RoomAdminRequiredError,
    RoomBannedError,
    RoomFullError,
    RoomLockedError,
    RoomNotFoundError,
    RoomSettingsLockedError,
)
from app.exceptions.templates import TemplateHasNoTilesError, TemplateNotFoundError
from app.models.game import Game
from app.models.room import Room
from app.models.round import Round
from app.models.snapshot_tile import SnapshotTile
from app.models.user import User
from app.schemas.rooms import (
    CreateRoomRequest,
    CurrentGameResponse,
    CurrentItemResponse,
    GuestRoomResponse,
    JoinAsGuestRequest,
    ParticipantResponse,
    RestoreGuestRequest,
    RoomBanResponse,
    RoomResponse,
    RoomSettingsResponse,
    RoomTemplateResponse,
    UpdateRoomSettingsRequest,
)
from app.services.games import GameService
from app.services.image_storage import ImageStorage
from app.services.rooms import GuestSeat, RoomService, RoomSettingsChanges, RoomViewer

router = APIRouter(prefix="/rooms", tags=["rooms"])

ROOM_NOT_FOUND_RESPONSES: dict[int | str, dict[str, Any]] = {
    **UNAUTHORIZED_RESPONSE,
    404: {"model": ErrorResponse, "description": messages.ROOM_NOT_FOUND_DESCRIPTION},
}
ROOM_ADMIN_REQUIRED_RESPONSE: dict[int | str, dict[str, Any]] = {
    403: {"model": ErrorResponse, "description": messages.ROOM_ADMIN_REQUIRED_DESCRIPTION},
}
ROOM_BANNED_RESPONSE: dict[int | str, dict[str, Any]] = {
    403: {"model": ErrorResponse, "description": messages.ROOM_BANNED_DESCRIPTION},
}

RoomServiceDep = Annotated[RoomService, Depends(get_room_service)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
RoomViewerDep = Annotated[RoomViewer, Depends(get_room_viewer)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
GameServiceDep = Annotated[GameService, Depends(get_game_service)]
# Donne l'adresse publique de l'image de l'item en cours
ImageStorageDep = Annotated[ImageStorage, Depends(get_image_storage)]


def _room_response(
    room: Room, user: User | None, service: RoomService, storage: ImageStorage
) -> RoomResponse:
    """La salle vue par ce lecteur : user est None pour un invité (jamais room admin)."""
    participants: list[ParticipantResponse] = []
    for participant in service.seated_participants(room):
        participant_response: ParticipantResponse = ParticipantResponse(
            id=participant.id,
            display_name=participant.display_name,
            is_admin=participant.user_id == room.admin_id,
            is_guest=participant.is_guest,
            connected=participant.connected,
        )
        participants.append(participant_response)
    # None une fois le template purgé
    template: RoomTemplateResponse | None = (
        RoomTemplateResponse.model_validate(room.template) if room.template is not None else None
    )
    settings: RoomSettingsResponse = RoomSettingsResponse.model_validate(room)
    link: str = service.link(room)
    is_admin: bool = user is not None and room.admin_id == user.id
    # Les bannissements ne regardent que le room admin
    bans: list[RoomBanResponse] = []
    if is_admin:
        for room_ban in room.bans:
            ban_response: RoomBanResponse = RoomBanResponse(
                id=room_ban.id, display_name=room_ban.display_name, is_guest=room_ban.is_guest
            )
            bans.append(ban_response)
    return RoomResponse(
        code=room.code,
        version=room.version,
        link=link,
        status=room.status,
        template=template,
        settings=settings,
        participants=participants,
        is_admin=is_admin,
        bans=bans,
        game=_current_game_response(room.current_game, storage),
    )


def _current_game_response(game: Game | None, storage: ImageStorage) -> CurrentGameResponse | None:
    """La partie en cours vue par tous : son tour et son item, jamais les placements."""
    if game is None:
        return None
    current_round: Round = game.current_round
    tile: SnapshotTile = current_round.tile
    image_url: str | None = storage.url(tile.image.storage_key) if tile.image is not None else None
    current_item: CurrentItemResponse = CurrentItemResponse(
        id=tile.id, text=tile.text, image_url=image_url
    )
    return CurrentGameResponse(
        round_number=current_round.number,
        round_count=len(game.rounds),
        current_item=current_item,
        ends_at=current_round.ends_at,
    )


def _set_guest_cookie(response: Response, seat: GuestSeat, settings: Settings) -> None:
    """Fait reconnaître l'invité par son navigateur (US-5.4) : cookie HttpOnly limité aux routes
    de sa salle, jusqu'à l'expiration de son lien perso."""
    expires_at: datetime | None = seat.participant.guest_expires_at
    if expires_at is None:
        raise RuntimeError("A guest seat has an expiry date")
    max_age: int = int((expires_at - datetime.now(UTC)).total_seconds())
    response.set_cookie(
        GUEST_COOKIE,
        seat.token,
        max_age=max_age,
        path=f"{settings.room_cookie_path}/{seat.room.code}",
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite="strict",
    )


def _room_not_found() -> AppHTTPException:
    return AppHTTPException(
        status_code=404,
        code=ErrorCode.ROOM_NOT_FOUND,
        detail=messages.ROOM_NOT_FOUND,
    )


def _room_admin_required() -> AppHTTPException:
    return AppHTTPException(
        status_code=403,
        code=ErrorCode.ROOM_ADMIN_REQUIRED,
        detail=messages.ROOM_ADMIN_REQUIRED,
    )


def _room_banned() -> AppHTTPException:
    return AppHTTPException(
        status_code=403,
        code=ErrorCode.ROOM_BANNED,
        detail=messages.ROOM_BANNED,
    )


def _room_full(exc: RoomFullError) -> AppHTTPException:
    return AppHTTPException(
        status_code=409,
        code=ErrorCode.ROOM_FULL,
        detail=messages.ROOM_FULL.format(max_participants=exc.max_participants),
        params={"max_participants": exc.max_participants},
    )


def _room_locked() -> AppHTTPException:
    return AppHTTPException(
        status_code=409,
        code=ErrorCode.ROOM_LOCKED,
        detail=messages.ROOM_LOCKED,
    )


@router.post(
    "",
    status_code=201,
    responses={
        **UNAUTHORIZED_RESPONSE,
        404: {"model": ErrorResponse, "description": messages.TEMPLATE_NOT_FOUND_DESCRIPTION},
        409: {"model": ErrorResponse, "description": messages.TEMPLATE_HAS_NO_TILES_DESCRIPTION},
    },
)
def create_room(
    payload: CreateRoomRequest,
    user: CurrentUserDep,
    service: RoomServiceDep,
    storage: ImageStorageDep,
) -> RoomResponse:
    template_id: uuid.UUID = payload.template_id
    try:
        room: Room = service.create(user, template_id)
    except TemplateNotFoundError as exc:
        raise AppHTTPException(
            status_code=404,
            code=ErrorCode.TEMPLATE_NOT_FOUND,
            detail=messages.TEMPLATE_NOT_FOUND,
        ) from exc
    except TemplateHasNoTilesError as exc:
        raise AppHTTPException(
            status_code=409,
            code=ErrorCode.TEMPLATE_HAS_NO_TILES,
            detail=messages.TEMPLATE_HAS_NO_TILES,
        ) from exc
    return _room_response(room, user, service, storage)


# Compte (access token) ou invité (cookie de sa salle) ; sans place, 404 comme un code inconnu
@router.get("/{code}", responses=ROOM_NOT_FOUND_RESPONSES)
def get_room(
    code: str, viewer: RoomViewerDep, service: RoomServiceDep, storage: ImageStorageDep
) -> RoomResponse:
    try:
        room: Room = service.get_for_viewer(viewer, code)
    except RoomNotFoundError as exc:
        raise _room_not_found() from exc
    return _room_response(room, viewer.user, service, storage)


@router.post(
    "/{code}/guests",
    status_code=201,
    responses={
        **ROOM_BANNED_RESPONSE,
        404: {"model": ErrorResponse, "description": messages.ROOM_NOT_FOUND_DESCRIPTION},
        409: {
            "model": ErrorResponse,
            "description": messages.NICKNAME_TAKEN_OR_ROOM_FULL_OR_LOCKED_DESCRIPTION,
        },
    },
)
def join_as_guest(
    code: str,
    payload: JoinAsGuestRequest,
    response: Response,
    service: RoomServiceDep,
    storage: ImageStorageDep,
    settings: SettingsDep,
    guest_token: Annotated[str | None, Cookie(alias=GUEST_COOKIE)] = None,
) -> GuestRoomResponse:
    # Sans compte : un pseudo suffit (US-2.5). Le cookie d'une place précédente fait reconnaître
    # le navigateur d'un invité banni (US-2.12)
    try:
        seat: GuestSeat = service.join_as_guest(code, payload.nickname, guest_token)
    except RoomNotFoundError as exc:
        raise _room_not_found() from exc
    except RoomBannedError as exc:
        raise _room_banned() from exc
    except RoomLockedError as exc:
        raise _room_locked() from exc
    except RoomFullError as exc:
        raise _room_full(exc) from exc
    except NicknameTakenError as exc:
        raise AppHTTPException(
            status_code=409,
            code=ErrorCode.NICKNAME_TAKEN,
            detail=messages.NICKNAME_TAKEN,
        ) from exc
    _set_guest_cookie(response, seat, settings)
    return _guest_room_response(seat, service, storage)


@router.post(
    "/{code}/guest-session",
    responses={
        404: {"model": ErrorResponse, "description": messages.GUEST_LINK_INVALID_DESCRIPTION},
    },
)
def restore_guest_session(
    code: str,
    payload: RestoreGuestRequest,
    response: Response,
    service: RoomServiceDep,
    storage: ImageStorageDep,
    settings: SettingsDep,
) -> GuestRoomResponse:
    # Lien perso ouvert sur un autre appareil (US-5.4) : le cookie y est posé à son tour
    try:
        seat: GuestSeat = service.restore_guest(code, payload.token)
    except GuestLinkInvalidError as exc:
        raise AppHTTPException(
            status_code=404,
            code=ErrorCode.GUEST_LINK_INVALID,
            detail=messages.GUEST_LINK_INVALID,
        ) from exc
    _set_guest_cookie(response, seat, settings)
    return _guest_room_response(seat, service, storage)


@router.post("/{code}/guest-link", responses=ROOM_NOT_FOUND_RESPONSES)
def renew_guest_link(
    code: str,
    viewer: RoomViewerDep,
    response: Response,
    service: RoomServiceDep,
    storage: ImageStorageDep,
    settings: SettingsDep,
) -> GuestRoomResponse:
    # Invité reconnu par son cookie qui a perdu son lien perso : l'ancien cesse de marcher
    try:
        seat: GuestSeat = service.renew_guest_link(viewer, code)
    except RoomNotFoundError as exc:
        raise _room_not_found() from exc
    _set_guest_cookie(response, seat, settings)
    return _guest_room_response(seat, service, storage)


def _guest_room_response(
    seat: GuestSeat, service: RoomService, storage: ImageStorage
) -> GuestRoomResponse:
    room_response: RoomResponse = _room_response(seat.room, None, service, storage)
    expires_at: datetime | None = seat.participant.guest_expires_at
    if expires_at is None:
        raise RuntimeError("A guest seat has an expiry date")
    return GuestRoomResponse(
        **room_response.model_dump(),
        guest_link=service.guest_link(seat),
        guest_link_expires_at=expires_at,
    )


@router.post(
    "/{code}/join",
    responses={
        **ROOM_NOT_FOUND_RESPONSES,
        **ROOM_BANNED_RESPONSE,
        409: {"model": ErrorResponse, "description": messages.ROOM_FULL_OR_LOCKED_DESCRIPTION},
    },
)
def join_room(
    code: str, user: CurrentUserDep, service: RoomServiceDep, storage: ImageStorageDep
) -> RoomResponse:
    # Rejoint comme joueur, ou retrouve sa place : appeler deux fois ne crée pas de seconde place
    try:
        room: Room = service.join(user, code)
    except RoomNotFoundError as exc:
        raise _room_not_found() from exc
    except RoomBannedError as exc:
        raise _room_banned() from exc
    except RoomLockedError as exc:
        raise _room_locked() from exc
    except RoomFullError as exc:
        raise _room_full(exc) from exc
    return _room_response(room, user, service, storage)


@router.patch(
    "/{code}/settings",
    responses={
        **ROOM_NOT_FOUND_RESPONSES,
        **ROOM_ADMIN_REQUIRED_RESPONSE,
        409: {"model": ErrorResponse, "description": messages.ROOM_SETTINGS_LOCKED_DESCRIPTION},
    },
)
def update_room_settings(
    code: str,
    payload: UpdateRoomSettingsRequest,
    user: CurrentUserDep,
    service: RoomServiceDep,
    storage: ImageStorageDep,
) -> RoomResponse:
    # Seuls les réglages envoyés (non nuls) changent
    changes: RoomSettingsChanges = RoomSettingsChanges(**payload.model_dump(exclude_none=True))
    try:
        room: Room = service.update_settings(user, code, changes)
    except RoomNotFoundError as exc:
        raise _room_not_found() from exc
    except RoomAdminRequiredError as exc:
        raise _room_admin_required() from exc
    except RoomSettingsLockedError as exc:
        raise AppHTTPException(
            status_code=409,
            code=ErrorCode.ROOM_SETTINGS_LOCKED,
            detail=messages.ROOM_SETTINGS_LOCKED,
        ) from exc
    return _room_response(room, user, service, storage)


@router.delete(
    "/{code}/participants/{participant_id}",
    responses={
        **UNAUTHORIZED_RESPONSE,
        **ROOM_ADMIN_REQUIRED_RESPONSE,
        404: {
            "model": ErrorResponse,
            "description": messages.ROOM_OR_PARTICIPANT_NOT_FOUND_DESCRIPTION,
        },
        409: {"model": ErrorResponse, "description": messages.CANNOT_REMOVE_ROOM_ADMIN_DESCRIPTION},
    },
)
def remove_participant(
    code: str,
    participant_id: uuid.UUID,
    user: CurrentUserDep,
    service: RoomServiceDep,
    storage: ImageStorageDep,
    ban: bool = False,
) -> RoomResponse:
    # Supprime la place (US-2.11) ; avec ban=true, la personne ne peut plus revenir (US-2.12)
    try:
        room: Room = service.remove_participant(user, code, participant_id, ban)
    except RoomNotFoundError as exc:
        raise _room_not_found() from exc
    except RoomAdminRequiredError as exc:
        raise _room_admin_required() from exc
    except ParticipantNotFoundError as exc:
        raise AppHTTPException(
            status_code=404,
            code=ErrorCode.PARTICIPANT_NOT_FOUND,
            detail=messages.PARTICIPANT_NOT_FOUND,
        ) from exc
    except CannotRemoveRoomAdminError as exc:
        raise AppHTTPException(
            status_code=409,
            code=ErrorCode.CANNOT_REMOVE_ROOM_ADMIN,
            detail=messages.CANNOT_REMOVE_ROOM_ADMIN,
        ) from exc
    return _room_response(room, user, service, storage)


@router.delete(
    "/{code}/bans/{ban_id}",
    responses={
        **UNAUTHORIZED_RESPONSE,
        **ROOM_ADMIN_REQUIRED_RESPONSE,
        404: {"model": ErrorResponse, "description": messages.ROOM_OR_BAN_NOT_FOUND_DESCRIPTION},
    },
)
def unban(
    code: str,
    ban_id: uuid.UUID,
    user: CurrentUserDep,
    service: RoomServiceDep,
    storage: ImageStorageDep,
) -> RoomResponse:
    try:
        room: Room = service.unban(user, code, ban_id)
    except RoomNotFoundError as exc:
        raise _room_not_found() from exc
    except RoomAdminRequiredError as exc:
        raise _room_admin_required() from exc
    except BanNotFoundError as exc:
        raise AppHTTPException(
            status_code=404,
            code=ErrorCode.BAN_NOT_FOUND,
            detail=messages.BAN_NOT_FOUND,
        ) from exc
    return _room_response(room, user, service, storage)


@router.post(
    "/{code}/game",
    status_code=201,
    responses={
        **ROOM_NOT_FOUND_RESPONSES,
        **ROOM_ADMIN_REQUIRED_RESPONSE,
        409: {"model": ErrorResponse, "description": messages.GAME_CANNOT_START_DESCRIPTION},
    },
)
def start_game(
    code: str,
    user: CurrentUserDep,
    games: GameServiceDep,
    service: RoomServiceDep,
    storage: ImageStorageDep,
) -> RoomResponse:
    # Le room admin lance une partie (US-3.1) : le premier item est montré à tous
    try:
        room: Room = games.start(user, code)
    except RoomNotFoundError as exc:
        raise _room_not_found() from exc
    except RoomAdminRequiredError as exc:
        raise _room_admin_required() from exc
    except GameInProgressError as exc:
        raise AppHTTPException(
            status_code=409,
            code=ErrorCode.GAME_IN_PROGRESS,
            detail=messages.GAME_IN_PROGRESS,
        ) from exc
    except NoPlacingParticipantError as exc:
        raise AppHTTPException(
            status_code=409,
            code=ErrorCode.NO_PLACING_PARTICIPANT,
            detail=messages.NO_PLACING_PARTICIPANT,
        ) from exc
    except TemplateNotFoundError as exc:
        raise AppHTTPException(
            status_code=409,
            code=ErrorCode.TEMPLATE_NOT_FOUND,
            detail=messages.TEMPLATE_NOT_FOUND,
        ) from exc
    except TemplateHasNoTilesError as exc:
        raise AppHTTPException(
            status_code=409,
            code=ErrorCode.TEMPLATE_HAS_NO_TILES,
            detail=messages.TEMPLATE_HAS_NO_TILES,
        ) from exc
    return _room_response(room, user, service, storage)
