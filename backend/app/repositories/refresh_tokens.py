import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.user import RefreshToken


def get_refresh_token_for_update(session: Session, token_hash: str) -> RefreshToken | None:
    # FOR UPDATE : deux rafraîchissements simultanés du même token sont traités l'un après
    # l'autre, le second voit donc le token déjà révoqué.
    statement = select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
    return session.scalars(statement).one_or_none()


def add_refresh_token(session: Session, refresh_token: RefreshToken) -> None:
    session.add(refresh_token)


def revoke_refresh_token_family(
    session: Session, family_id: uuid.UUID, revoked_at: datetime
) -> None:
    session.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=revoked_at)
    )
