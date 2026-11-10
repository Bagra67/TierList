from app.core.config import Settings

REQUIRED_SETTINGS: dict[str, object] = {
    "postgres_user": "tierlist",
    "postgres_password": "unit-test-password",
    "postgres_db": "tierlist",
    "jwt_secret_key": "unit-test-secret-key-of-at-least-32-chars",
}


def make_settings(**overrides: object) -> Settings:
    return Settings.model_validate({**REQUIRED_SETTINGS, **overrides})
