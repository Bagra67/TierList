"""Le canal temps réel sans effet : le jeu de données crée et remplit des salles où aucun
navigateur n'est connecté."""

import uuid

from app.constants.error_codes import ErrorCode
from app.schemas.room_events import RoomEvent


class NoOpRoomEventPublisher:
    def publish(self, room_id: uuid.UUID, event: RoomEvent) -> None:
        pass

    def disconnect_participant(
        self, room_id: uuid.UUID, participant_id: uuid.UUID, close_code: int, reason: ErrorCode
    ) -> None:
        pass

    def close_room(self, room_id: uuid.UUID) -> None:
        pass
