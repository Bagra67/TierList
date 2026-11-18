from dataclasses import dataclass

from app.constants.i18n import Language


@dataclass(frozen=True)
class PageTexts:
    site_title: str
    site_description: str
    marketplace_title: str
    privacy_title: str
    terms_title: str
    legal_notice_title: str
    template_description: str


PAGE_TEXTS: dict[Language, PageTexts] = {
    "fr": PageTexts(
        site_title="TierList · Classez ensemble, en direct",
        site_description=(
            "Chacun place les mêmes éléments dans sa tier list, sans voir celle des autres. "
            "À la fin, vous comparez qui a mis quoi, et où."
        ),
        marketplace_title="Modèles publics",
        privacy_title="Politique de confidentialité",
        terms_title="Conditions d'utilisation",
        legal_notice_title="Mentions légales",
        template_description=(
            "Modèle de tier list « {name} », par {owner}. Classez ses éléments ensemble, "
            "en direct, sur TierList."
        ),
    ),
    "en": PageTexts(
        site_title="TierList · Rank together, live",
        site_description=(
            "Everyone places the same items in their own tier list, without seeing the "
            "others'. At the end, you compare who put what, and where."
        ),
        marketplace_title="Public templates",
        privacy_title="Privacy policy",
        terms_title="Terms of use",
        legal_notice_title="Legal notice",
        template_description=(
            "“{name}” tier list template by {owner}. Rank its items together, live, on TierList."
        ),
    ),
}
