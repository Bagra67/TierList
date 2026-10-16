from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.oauth_account import OAuthAccount
from app.models.user import User


def get_user_by_oauth_account(
    session: Session, provider: str, provider_subject: str
) -> User | None:
    statement = (
        select(User)
        .join(OAuthAccount, OAuthAccount.user_id == User.id)
        .where(OAuthAccount.provider == provider, OAuthAccount.provider_subject == provider_subject)
    )
    return session.scalars(statement).one_or_none()


def add_oauth_account(session: Session, oauth_account: OAuthAccount) -> None:
    session.add(oauth_account)
    # Flush : déclenche tout de suite la contrainte d'unicité (provider, provider_subject)
    session.flush()
