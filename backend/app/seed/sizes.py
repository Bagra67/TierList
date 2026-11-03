from dataclasses import dataclass


@dataclass(frozen=True)
class SeedSize:
    super_admins: int
    players: int
    unverified_accounts: int
    google_accounts: int
    empty_templates: int
    text_templates: int
    image_templates: int
    full_templates: int
    deleted_templates: int
    image_tiles_per_template: int
    closed_games: int
    history_games: int
    open_rooms_with_past_games: int
    full_rooms: int
    rooms_with_bans: int
    moderation_actions: int
    hidden_images: int
    deleted_images: int
    hidden_templates: int
    temporarily_banned_accounts: int
    permanently_banned_accounts: int
    accounts_with_a_lifted_ban: int
    reported_images: int
    reported_nicknames: int
    reported_games: int
    reports_on_most_reported_content: int


FULL_SIZE: SeedSize = SeedSize(
    super_admins=6,
    players=24,
    unverified_accounts=3,
    google_accounts=3,
    empty_templates=3,
    text_templates=9,
    image_templates=6,
    full_templates=6,
    deleted_templates=6,
    image_tiles_per_template=12,
    closed_games=75,
    history_games=62,
    open_rooms_with_past_games=3,
    full_rooms=3,
    rooms_with_bans=3,
    moderation_actions=180,
    hidden_images=3,
    deleted_images=1,
    hidden_templates=2,
    temporarily_banned_accounts=1,
    permanently_banned_accounts=1,
    accounts_with_a_lifted_ban=1,
    reported_images=6,
    reported_nicknames=3,
    reported_games=3,
    reports_on_most_reported_content=5,
)

SMALL_SIZE: SeedSize = SeedSize(
    super_admins=2,
    players=8,
    unverified_accounts=1,
    google_accounts=1,
    empty_templates=1,
    text_templates=2,
    image_templates=1,
    full_templates=1,
    deleted_templates=1,
    image_tiles_per_template=3,
    closed_games=23,
    history_games=22,
    open_rooms_with_past_games=1,
    full_rooms=1,
    rooms_with_bans=1,
    moderation_actions=60,
    hidden_images=1,
    deleted_images=1,
    hidden_templates=1,
    temporarily_banned_accounts=1,
    permanently_banned_accounts=1,
    accounts_with_a_lifted_ban=1,
    reported_images=1,
    reported_nicknames=1,
    reported_games=1,
    reports_on_most_reported_content=3,
)
