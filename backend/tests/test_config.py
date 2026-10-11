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


IMAGE_SETTINGS_ENV_VARS: tuple[str, ...] = (
    "IMAGE_UPLOAD_MAX_BYTES",
    "IMAGE_MAX_SOURCE_PIXELS",
    "IMAGE_S3_ENDPOINT_URL",
    "IMAGE_S3_BUCKET",
    "IMAGE_S3_REGION",
    "IMAGE_S3_ACCESS_KEY_ID",
    "IMAGE_S3_SECRET_ACCESS_KEY",
    "IMAGE_S3_TIMEOUT_SECONDS",
    "IMAGE_PUBLIC_BASE_URL",
)


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


@pytest.mark.parametrize(
    "field_name",
    ["image_upload_max_bytes", "image_max_source_pixels", "image_s3_timeout_seconds"],
)
@pytest.mark.parametrize("invalid_value", [0, -1])
def test_image_limits_must_be_positive(field_name: str, invalid_value: int) -> None:
    with pytest.raises(ValidationError):
        make_settings(**{field_name: invalid_value})


def test_image_storage_defaults_to_the_development_bucket_without_credentials() -> None:
    settings: Settings = make_settings()

    # Sans adresse ni clés, boto3 vise AWS S3 avec ses identifiants habituels
    assert settings.image_s3_endpoint_url is None
    assert settings.image_s3_access_key_id is None
    assert settings.image_s3_secret_access_key is None
    assert settings.image_s3_bucket == "tierlist-images"
    assert settings.image_s3_region == "us-east-1"
    assert settings.image_s3_timeout_seconds == 10
    assert settings.image_public_base_url == "http://127.0.0.1:8333/tierlist-images"


def test_the_s3_secret_key_is_hidden_when_printed() -> None:
    settings: Settings = make_settings(image_s3_secret_access_key="very-secret-key")

    assert "very-secret-key" not in repr(settings)
    assert settings.image_s3_secret_access_key is not None
    assert settings.image_s3_secret_access_key.get_secret_value() == "very-secret-key"
