from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Classe de base des modèles ORM ; sa metadata est la cible des migrations Alembic."""
