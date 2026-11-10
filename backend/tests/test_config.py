from ipaddress import ip_network
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.db import session as session_module
from tests.settings_factory import make_settings

IMAGE_SETTINGS_ENV_VARS: tuple[str, ...] = (
    "IMAGE_UPLOAD_MAX_BYTES",
    "IMAGE_MAX_SOURCE_PIXELS",
    "IMAGE_UPLOADS_PER_HOUR_MAX",
    "UNUSED_IMAGE_RETENTION_DAYS",
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
    monkeypatch.chdir(tmp_path)
    for env_var in IMAGE_SETTINGS_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)


def test_image_settings_default_to_the_decided_limits() -> None:
    settings: Settings = make_settings()

    assert settings.image_upload_max_bytes == 10 * 1024 * 1024
    assert settings.image_max_source_pixels == 40_000_000
    assert settings.image_uploads_per_hour_max == 120
    assert settings.unused_image_retention_days == 7


@pytest.mark.parametrize(
    "field_name",
    [
        "image_upload_max_bytes",
        "image_max_source_pixels",
        "image_uploads_per_hour_max",
        "unused_image_retention_days",
        "image_s3_timeout_seconds",
    ],
)
@pytest.mark.parametrize("invalid_value", [0, -1])
def test_image_limits_must_be_positive(field_name: str, invalid_value: int) -> None:
    with pytest.raises(ValidationError):
        make_settings(**{field_name: invalid_value})


def test_image_storage_defaults_to_the_development_bucket_without_credentials() -> None:
    settings: Settings = make_settings()

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


def test_no_trusted_proxy_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TRUSTED_PROXY_IPS", raising=False)

    assert make_settings().trusted_proxy_ips == []


def test_trusted_proxies_are_read_from_a_comma_separated_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_IPS", "10.0.0.7, 10.1.0.0/16")

    assert make_settings().trusted_proxy_ips == [
        ip_network("10.0.0.7/32"),
        ip_network("10.1.0.0/16"),
    ]


@pytest.mark.parametrize("invalid_value", ["*", "not-an-address", "10.0.0.300"])
def test_an_invalid_trusted_proxy_is_refused(
    monkeypatch: pytest.MonkeyPatch, invalid_value: str
) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_IPS", invalid_value)

    with pytest.raises(ValidationError):
        make_settings()


def test_the_moderation_log_is_kept_the_3_years_stated_by_the_privacy_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MODERATION_LOG_RETENTION_DAYS", raising=False)

    assert make_settings().moderation_log_retention_days == 3 * 365


@pytest.mark.parametrize("invalid_value", [0, -1])
def test_the_moderation_log_retention_must_be_positive(invalid_value: int) -> None:
    with pytest.raises(ValidationError):
        make_settings(moderation_log_retention_days=invalid_value)


def test_the_engine_uses_the_connect_timeout_and_hides_the_query_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings: Settings = make_settings(database_connect_timeout_seconds=7)
    engine_arguments: dict[str, object] = {}

    def record_engine_arguments(url: object, **arguments: object) -> None:
        engine_arguments.update(arguments)

    def settings_of_the_test() -> Settings:
        return settings

    monkeypatch.setattr(session_module, "create_engine", record_engine_arguments)
    monkeypatch.setattr(session_module, "get_settings", settings_of_the_test)

    session_module.get_engine.__wrapped__()

    assert engine_arguments["connect_args"] == {"connect_timeout": 7}
    assert engine_arguments["hide_parameters"] is True
