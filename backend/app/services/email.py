"""Envoi des emails transactionnels par SMTP (docs/technical/emails.md).

Le fournisseur (Brevo, Resend, Amazon SES…) n'est qu'une configuration SMTP : en changer ne
demande pas de modifier le code. En développement, Mailpit reçoit les emails sans les distribuer.
"""

import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage

from app.core.config import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    # Version texte, lue par les clients qui n'affichent pas le HTML
    text: str
    html: str


class EmailSender:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send(self, email: Email) -> None:
        """Envoie l'email ; un échec est journalisé, jamais levé.

        L'envoi a lieu en tâche de fond, après la réponse : personne ne pourrait traiter
        l'erreur, et l'utilisateur peut redemander l'email.
        """
        settings = self._settings
        if settings.smtp_host is None:
            logger.warning("Email non envoyé : SMTP_HOST n'est pas configuré")
            return
        try:
            with smtplib.SMTP(
                settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds
            ) as smtp:
                if settings.smtp_starttls:
                    smtp.starttls(context=ssl.create_default_context())
                if settings.smtp_username is not None and settings.smtp_password is not None:
                    smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
                smtp.send_message(self._build_message(email))
        except (smtplib.SMTPException, OSError) as exc:
            # Seul le type d'erreur est journalisé : le message SMTP peut contenir l'adresse
            logger.error("Échec de l'envoi d'un email : %s", type(exc).__name__)

    def _build_message(self, email: Email) -> EmailMessage:
        message = EmailMessage()
        message["From"] = self._settings.email_from
        message["To"] = email.to
        message["Subject"] = email.subject
        message.set_content(email.text)
        message.add_alternative(email.html, subtype="html")
        return message
