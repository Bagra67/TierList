# Importer chaque module de modèles ici : migrations/env.py importe ce paquet pour que
# --autogenerate voie toutes les tables de Base.metadata.
from app.models.game import Game
from app.models.game_player import GamePlayer
from app.models.image import Image
from app.models.oauth_account import OAuthAccount
from app.models.participant import Participant
from app.models.placement import Placement
from app.models.refresh_token import RefreshToken
from app.models.room import Room
from app.models.room_ban import RoomBan
from app.models.round import Round
from app.models.snapshot_tier import SnapshotTier
from app.models.snapshot_tile import SnapshotTile
from app.models.template import Template
from app.models.template_snapshot import TemplateSnapshot
from app.models.tier import Tier
from app.models.tile import Tile
from app.models.user import User

__all__ = [
    "Game",
    "GamePlayer",
    "Image",
    "OAuthAccount",
    "Participant",
    "Placement",
    "RefreshToken",
    "Room",
    "RoomBan",
    "Round",
    "SnapshotTier",
    "SnapshotTile",
    "Template",
    "TemplateSnapshot",
    "Tier",
    "Tile",
    "User",
]
