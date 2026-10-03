from dataclasses import dataclass
from html import escape

from app.constants.i18n import Language
from app.services.email import Email


@dataclass(frozen=True)
class _LinkEmailTexts:
    """Textes d'un email qui invite à ouvrir un lien ; {name} et la durée sont remplacés."""

    subject: str
    greeting: str
    body: str
    button: str
    footer: str


_VERIFICATION_TEXTS: dict[Language, _LinkEmailTexts] = {
    "fr": _LinkEmailTexts(
        subject="Confirmez votre adresse email",
        greeting="Bonjour {name},",
        body=(
            "Pour confirmer l'adresse de votre compte TierList, ouvrez le lien ci-dessous. "
            "Il est valable {hours} heures."
        ),
        button="Confirmer mon adresse",
        footer="Si vous n'avez pas créé de compte TierList, ignorez cet email.",
    ),
    "en": _LinkEmailTexts(
        subject="Confirm your email address",
        greeting="Hello {name},",
        body=(
            "To confirm the address of your TierList account, open the link below. "
            "It is valid for {hours} hours."
        ),
        button="Confirm my address",
        footer="If you did not create a TierList account, ignore this email.",
    ),
}


_PASSWORD_RESET_TEXTS: dict[Language, _LinkEmailTexts] = {
    "fr": _LinkEmailTexts(
        subject="Choisissez un nouveau mot de passe",
        greeting="Bonjour {name},",
        body=(
            "Pour choisir un nouveau mot de passe pour votre compte TierList, ouvrez le lien "
            "ci-dessous. Il est valable {minutes} minutes et ne sert qu'une fois."
        ),
        button="Choisir un nouveau mot de passe",
        footer=(
            "Si vous n'avez rien demandé, ignorez cet email : votre mot de passe actuel reste "
            "valable."
        ),
    ),
    "en": _LinkEmailTexts(
        subject="Choose a new password",
        greeting="Hello {name},",
        body=(
            "To choose a new password for your TierList account, open the link below. "
            "It is valid for {minutes} minutes and works only once."
        ),
        button="Choose a new password",
        footer=(
            "If you did not ask for anything, ignore this email: your current password still works."
        ),
    ),
}


def _link_email(
    texts: _LinkEmailTexts, *, to: str, display_name: str, link: str, **duration: int
) -> Email:
    greeting = texts.greeting.format(name=display_name)
    body = texts.body.format(**duration)
    text = f"{greeting}\n\n{body}\n\n{link}\n\n{texts.footer}\n"
    # Le nom affiché est choisi par l'utilisateur : échappé, il ne peut pas injecter de HTML
    html = (
        f"<p>{escape(greeting)}</p>"
        f"<p>{escape(body)}</p>"
        f'<p><a href="{escape(link)}">{escape(texts.button)}</a></p>'
        f"<p>{escape(texts.footer)}</p>"
    )
    return Email(to=to, subject=texts.subject, text=text, html=html)


def verification_email(
    language: Language, *, to: str, display_name: str, link: str, ttl_hours: int
) -> Email:
    return _link_email(
        _VERIFICATION_TEXTS[language], to=to, display_name=display_name, link=link, hours=ttl_hours
    )


def password_reset_email(
    language: Language, *, to: str, display_name: str, link: str, ttl_minutes: int
) -> Email:
    return _link_email(
        _PASSWORD_RESET_TEXTS[language],
        to=to,
        display_name=display_name,
        link=link,
        minutes=ttl_minutes,
    )
