from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings

# Seuls les champs obligatoires : les autres prennent leur valeur par défaut
REQUIRED_SETTINGS: dict[str, object] = {
    "postgres_user": "tierlist",
    "postgres_password": "unit-test-password",
    "postgres_db": "tierlist",
    "jwt_secret_key": "unit-test-secret-key-of-at-least-32-chars",
}


IMAGE_SETTINGS_ENV_VARS: tuple[str, ...] = ("IMAGE_UPLOAD_MAX_BYTES", "IMAGE_MAX_SOURCE_PIXELS")


@pytest.fixture(autouse=True)
def isolate_from_local_configuration(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Settings lit l'environnement et le .env du dossier courant : un dossier vide et des variables
    # retirées garantissent que seules les valeurs par défaut du code sont testées
    monkeypatch.chdir(tmp_path)
    for env_var in IMAGE_SETTINGS_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)


def make_settings(**overrides: object) -> Settings:
    return Settings.model_validate({**REQUIRED_SETTINGS, **overrides})


def test_image_settings_default_to_the_decided_limits() -> None:
    settings: Settings = make_settings()

    assert settings.image_upload_max_bytes == 10 * 1024 * 1024
    assert settings.image_max_source_pixels == 40_000_000


@pytest.mark.parametrize("field_name", ["image_upload_max_bytes", "image_max_source_pixels"])
@pytest.mark.parametrize("invalid_value", [0, -1])
def test_image_limits_must_be_positive(field_name: str, invalid_value: int) -> None:
    with pytest.raises(ValidationError):
        make_settings(**{field_name: invalid_value})
