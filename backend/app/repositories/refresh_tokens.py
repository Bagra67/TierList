import uuid
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.models.user import RefreshToken


def get_refresh_token_for_update(session: Session, token_hash: str) -> RefreshToken | None:
    # FOR UPDATE : deux rafraîchissements simultanés du même token sont traités l'un après
    # l'autre, le second voit donc le token déjà révoqué.
    statement = select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
    return session.scalars(statement).one_or_none()


def add_refresh_token(session: Session, refresh_token: RefreshToken) -> None:
    session.add(refresh_token)


def delete_expired_user_refresh_tokens(session: Session, user_id: uuid.UUID, now: datetime) -> None:
    """Supprime les refresh tokens expirés de l'utilisateur, qui ne servent plus à rien."""
    session.execute(
        delete(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.expires_at <= now)
    )


def revoke_user_refresh_tokens(session: Session, user_id: uuid.UUID, revoked_at: datetime) -> None:
    """Ferme toutes les sessions de l'utilisateur."""
    session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=revoked_at)
    )


def revoke_refresh_token_family(
    session: Session, family_id: uuid.UUID, revoked_at: datetime
) -> None:
    session.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=revoked_at)
    )
