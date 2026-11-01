"""Forme canonique d'une adresse e-mail, partagée par l'authentification et les commandes qui
cherchent un compte par son adresse (scripts/set_super_admin.py)."""


def normalize_email(email: str) -> str:
    """Adresses enregistrées en minuscules : l'unicité et la recherche ignorent la casse."""
    return email.strip().lower()
