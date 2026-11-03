import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.constants.auth import GOOGLE_PROVIDER
from app.constants.i18n import DEFAULT_LANGUAGE
from app.core.config import Settings
from app.models.enums import UserRole
from app.models.oauth_account import OAuthAccount
from app.models.user import User
from app.repositories import users as user_repository
from app.seed.sizes import SeedSize
from app.services.auth import AuthService

logger = logging.getLogger(__name__)

SEED_EMAIL_PREFIX = "seed-"
SEED_EMAIL_DOMAIN = "@seed.example.com"

FIRST_NAMES: tuple[str, ...] = (
    "Alice", "Bastien", "Chloé", "David", "Emma", "Farid", "Gabrielle", "Hugo", "Inès", "Julien",
    "Karima", "Louis", "Manon", "Nathan", "Océane", "Paul", "Quentin", "Rose", "Sami", "Théo",
    "Ursula", "Victor", "Wassim", "Yasmine", "Zoé", "Adam", "Léna", "Malo", "Nora", "Simon",
)  # fmt: skip
SUPER_ADMIN_NAMES: tuple[str, ...] = ("Nina", "Samuel", "Margaux", "Karim", "Lucie", "Antoine")


def seed_email(kind: str, number: int) -> str:
    return f"{SEED_EMAIL_PREFIX}{kind}-{number}{SEED_EMAIL_DOMAIN}"


@dataclass(frozen=True)
class SeedAccounts:
    super_admins: list[User]
    players: list[User]
    unverified: list[User]
    google: list[User]


def create_accounts(
    session: Session, settings: Settings, size: SeedSize, password: str
) -> SeedAccounts:
    auth: AuthService = AuthService(session, settings)

    def register(kind: str, number: int, display_name: str, verified: bool) -> User:
        email: str = seed_email(kind, number)
        # L'e-mail de vérification renvoyé n'est jamais envoyé
        auth.register(email, password, display_name, DEFAULT_LANGUAGE)
        user: User | None = user_repository.get_user_by_email(session, email)
        assert user is not None
        if verified:
            user.email_verified_at = datetime.now(UTC)
        return user

    logger.info(
        "Comptes : %d super admins, %d joueurs, %d non confirmés, %d Google",
        size.super_admins,
        size.players,
        size.unverified_accounts,
        size.google_accounts,
    )
    super_admins: list[User] = []
    for number in range(1, size.super_admins + 1):
        name: str = SUPER_ADMIN_NAMES[(number - 1) % len(SUPER_ADMIN_NAMES)]
        super_admin: User = register("admin", number, name, verified=True)
        super_admin.role = UserRole.SUPER_ADMIN
        super_admins.append(super_admin)
    players: list[User] = [
        register("player", number, FIRST_NAMES[(number - 1) % len(FIRST_NAMES)], verified=True)
        for number in range(1, size.players + 1)
    ]
    unverified: list[User] = [
        register("unverified", number, f"Nouveau {number}", verified=False)
        for number in range(1, size.unverified_accounts + 1)
    ]
    google: list[User] = [
        _create_google_account(session, number) for number in range(1, size.google_accounts + 1)
    ]
    session.commit()
    logger.info("Comptes créés")
    return SeedAccounts(
        super_admins=super_admins, players=players, unverified=unverified, google=google
    )


def _create_google_account(session: Session, number: int) -> User:
    email: str = seed_email("google", number)
    user: User = User(
        email=email,
        password_hash=None,
        display_name=f"Google {number}",
        email_verified_at=datetime.now(UTC),
    )
    session.add(user)
    session.flush()
    session.add(
        OAuthAccount(
            user_id=user.id,
            provider=GOOGLE_PROVIDER,
            provider_subject=f"seed-google-subject-{number}",
            email=email,
        )
    )
    return user
