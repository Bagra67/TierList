import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user, get_room_service
from app.api.responses import UNAUTHORIZED_RESPONSE
from app.constants import messages
from app.constants.error_codes import ErrorCode
from app.core.errors import ErrorResponse
from app.exceptions.http import AppHTTPException
from app.exceptions.rooms import RoomAdminRequiredError, RoomNotFoundError, RoomSettingsLockedError
from app.exceptions.templates import TemplateHasNoTilesError, TemplateNotFoundError
from app.models.room import Room
from app.models.user import User
from app.schemas.rooms import (
    CreateRoomRequest,
    ParticipantResponse,
    RoomResponse,
    RoomSettingsResponse,
    RoomTemplateResponse,
    UpdateRoomSettingsRequest,
)
from app.services.rooms import RoomService, RoomSettingsChanges

router = APIRouter(prefix="/rooms", tags=["rooms"])

ROOM_NOT_FOUND_RESPONSES: dict[int | str, dict[str, Any]] = {
    **UNAUTHORIZED_RESPONSE,
    404: {"model": ErrorResponse, "description": messages.ROOM_NOT_FOUND_DESCRIPTION},
}

RoomServiceDep = Annotated[RoomService, Depends(get_room_service)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


def _room_response(room: Room, user: User, service: RoomService) -> RoomResponse:
    participants: list[ParticipantResponse] = []
    for participant in room.participants:
        participants.append(
            ParticipantResponse(
                id=participant.id,
                display_name=participant.user.display_name,
                is_admin=participant.user_id == room.admin_id,
            )
        )
    template: RoomTemplateResponse | None = None
    if room.template is not None:
        template = RoomTemplateResponse.model_validate(room.template)
    return RoomResponse(
        code=room.code,
        link=service.link(room),
        status=room.status,
        template=template,
        settings=RoomSettingsResponse.model_validate(room),
        participants=participants,
        is_admin=room.admin_id == user.id,
    )


def _room_not_found() -> AppHTTPException:
    return AppHTTPException(
        status_code=404,
        code=ErrorCode.ROOM_NOT_FOUND,
        detail=messages.ROOM_NOT_FOUND,
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
    payload: CreateRoomRequest, user: CurrentUserDep, service: RoomServiceDep
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
    return _room_response(room, user, service)


@router.get("/{code}", responses=ROOM_NOT_FOUND_RESPONSES)
def get_room(code: str, user: CurrentUserDep, service: RoomServiceDep) -> RoomResponse:
    try:
        room: Room = service.get(user, code)
    except RoomNotFoundError as exc:
        raise _room_not_found() from exc
    return _room_response(room, user, service)


@router.patch(
    "/{code}/settings",
    responses={
        **ROOM_NOT_FOUND_RESPONSES,
        403: {"model": ErrorResponse, "description": messages.ROOM_ADMIN_REQUIRED_DESCRIPTION},
        409: {"model": ErrorResponse, "description": messages.ROOM_SETTINGS_LOCKED_DESCRIPTION},
    },
)
def update_room_settings(
    code: str,
    payload: UpdateRoomSettingsRequest,
    user: CurrentUserDep,
    service: RoomServiceDep,
) -> RoomResponse:
    # Seuls les réglages envoyés (non nuls) changent
    changes: RoomSettingsChanges = RoomSettingsChanges(**payload.model_dump(exclude_none=True))
    try:
        room: Room = service.update_settings(user, code, changes)
    except RoomNotFoundError as exc:
        raise _room_not_found() from exc
    except RoomAdminRequiredError as exc:
        raise AppHTTPException(
            status_code=403,
            code=ErrorCode.ROOM_ADMIN_REQUIRED,
            detail=messages.ROOM_ADMIN_REQUIRED,
        ) from exc
    except RoomSettingsLockedError as exc:
        raise AppHTTPException(
            status_code=409,
            code=ErrorCode.ROOM_SETTINGS_LOCKED,
            detail=messages.ROOM_SETTINGS_LOCKED,
        ) from exc
    return _room_response(room, user, service)
