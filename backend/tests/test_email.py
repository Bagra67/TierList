import smtplib
from email.message import EmailMessage
from typing import Self

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.services import email as email_module
from app.services.email import Email, EmailSender

EMAIL = Email(
    to="alice@example.com",
    subject="Bienvenue",
    text="Bonjour Alice",
    html="<p>Bonjour Alice</p>",
)


class FakeSMTP:
    """Remplace smtplib.SMTP : garde les appels au lieu de contacter un serveur."""

    instances: list["FakeSMTP"] = []

    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.host, self.port, self.timeout = host, port, timeout
        self.started_tls = False
        self.login_args: tuple[str, str] | None = None
        self.sent: list[EmailMessage] = []
        FakeSMTP.instances.append(self)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def starttls(self, context: object) -> None:
        self.started_tls = True

    def login(self, user: str, password: str) -> None:
        self.login_args = (user, password)

    def send_message(self, message: EmailMessage) -> None:
        self.sent.append(message)


@pytest.fixture(autouse=True)
def fake_smtp(monkeypatch: pytest.MonkeyPatch) -> type[FakeSMTP]:
    FakeSMTP.instances = []
    monkeypatch.setattr(email_module.smtplib, "SMTP", FakeSMTP)
    return FakeSMTP


def smtp_settings(**changes: object) -> Settings:
    # model_construct : réglages SMTP seuls, sans les variables obligatoires de la base
    settings = Settings.model_construct(
        smtp_host="smtp.example.com", email_from="TierList <no-reply@example.com>"
    )
    return settings.model_copy(update=changes)


def test_sends_a_text_and_html_email_through_starttls():
    EmailSender(smtp_settings()).send(EMAIL)

    [smtp] = FakeSMTP.instances
    assert (smtp.host, smtp.port, smtp.timeout) == ("smtp.example.com", 587, 10)
    assert smtp.started_tls
    assert smtp.login_args is None
    [message] = smtp.sent
    assert message["From"] == "TierList <no-reply@example.com>"
    assert message["To"] == "alice@example.com"
    assert message["Subject"] == "Bienvenue"
    text_part = message.get_body(preferencelist=("plain",))
    html_part = message.get_body(preferencelist=("html",))
    assert text_part is not None and html_part is not None
    assert text_part.get_content().strip() == "Bonjour Alice"
    assert html_part.get_content().strip() == "<p>Bonjour Alice</p>"


def test_signs_in_when_credentials_are_configured():
    settings = smtp_settings(smtp_username="api-user", smtp_password=SecretStr("api-key"))

    EmailSender(settings).send(EMAIL)

    assert FakeSMTP.instances[0].login_args == ("api-user", "api-key")


def test_local_mailpit_needs_neither_tls_nor_credentials():
    EmailSender(smtp_settings(smtp_port=1025, smtp_starttls=False)).send(EMAIL)

    [smtp] = FakeSMTP.instances
    assert smtp.port == 1025
    assert not smtp.started_tls
    assert len(smtp.sent) == 1


def test_nothing_is_sent_without_smtp_host(caplog: pytest.LogCaptureFixture):
    EmailSender(Settings.model_construct()).send(EMAIL)

    assert FakeSMTP.instances == []
    assert "SMTP_HOST" in caplog.text


def test_a_smtp_failure_is_logged_without_the_address(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    def refuse(self: FakeSMTP, message: EmailMessage) -> None:
        raise smtplib.SMTPRecipientsRefused({EMAIL.to: (550, b"no such user")})

    monkeypatch.setattr(FakeSMTP, "send_message", refuse)

    EmailSender(smtp_settings()).send(EMAIL)

    assert "SMTPRecipientsRefused" in caplog.text
    assert EMAIL.to not in caplog.text
