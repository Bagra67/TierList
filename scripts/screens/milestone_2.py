"""Wireframes du jalon 2 (docs/product/milestone-2/screens/), sur la charte « Le Plateau ».

Depuis la racine du dépôt, après pnpm install dans frontend/ :
    uv run --project backend python scripts/screens/milestone_2.py
Écrit les 8 écrans en anglais et en français ; décrits dans docs/product/milestone-2/screens.md.
Les textes déjà dans l'application viennent des traductions ; les nouveaux, validés sur les
maquettes, sont dans COPY tant que leurs clés n'existent pas (à remplacer par t() ensuite).
"""

import os

from plateau import (
    BORDER,
    CARD,
    DESTRUCTIVE,
    HEAD,
    INK,
    INPUT,
    MUTED,
    MUTED_FG,
    PRIMARY,
    REPO_ROOT,
    TIERS,
    Screen,
    Svg,
    Translator,
    build,
    button,
    button_width,
    checkbox,
    dot,
    field,
    header,
    icon,
    panel,
    radio,
    tag,
    text_width,
    wrap,
)

OUT_DIR: str = os.path.join(REPO_ROOT, "docs", "product", "milestone-2", "screens")
WARNING_BG, WARNING_LINE, DANGER_BG = "#FFF1C7", "#AD7300", "#FBE3EA"

COPY: dict[str, dict[str, str]] = {
    "en": {
        "public": "Public templates",
        "public_intro": "Find a tier list to play with your friends, or an idea to make your own.",
        "search": "Search for a template",
        "sort": "Sort by",
        "most_liked": "Most liked",
        "by": "by {owner} · {count} items",
        "lineage": "by Camille · copied from “Chips de l'apéro” by Noé",
        "items": "Items (12)",
        "start_room": "Create a room with this template",
        "like": "Like · 128",
        "favorite": "Favorite",
        "copy": "Copy to my templates",
        "copy_hint": "Your copy is private; it shows which template it comes from.",
        "report_link": "Report this template",
        "visibility": "Visibility",
        "private": "Private: only you can start a room with it",
        "public_choice": "Public: everyone can find it and play it",
        "allow_copies": "Allow copies of this template",
        "tags_field": "Tags (5 at most)",
        "add_tag": "Add a tag",
        "tags_hint": "A word or a short phrase: people find your template by its tags.",
        "public_since": "Public since October 31, 2026 · 128 likes",
        "other_states": "Other states",
        "unconfirmed": "Confirm your email address to make a template public.",
        "hidden": "Hidden by moderation: someone else's images published without consent.",
        "hidden_hint": "You can still edit it, but not make it public again.",
        "report_title": "Report this template",
        "report_intro": "Your report is anonymous: the reported person will not know who sent it.",
        "reason": "Reason",
        "reasons": "Illegal content|Sexual content|Violence or hate|Harassment|Spam|Other",
        "details": "Details (optional)",
        "send": "Send the report",
        "moderation": "Moderation",
        "reports": "Reports",
        "uploads": "Recent uploads",
        "log": "Log",
        "reports_intro": "Open reports, grouped by content, the most reported first. "
        "Every decision is written to the log.",
        "kind_template": "Template",
        "kind_image": "Image",
        "kind_nickname": "Nickname",
        "report_1": "Top 10 worst teachers",
        "report_2": "image of the “Barbecue” tile",
        "report_3": "“xX_spam_Xx” in room K7P2QX",
        "from": "from {owner} · {count} reports",
        "from_one": "from {owner} · 1 report",
        "guest": "guest",
        "harassment": "Harassment ×4",
        "other": "Other ×1",
        "sexual": "Sexual content ×2",
        "spam": "Spam ×1",
        "dismiss": "Dismiss",
        "hide": "Hide",
        "delete": "Delete",
        "see_account": "See the account",
        "open_reports": "3 open reports",
        "no_sanction": "no sanction",
        "display_name": "Display name",
        "email": "Email",
        "created": "Created on",
        "created_value": "September 2, 2026",
        "confirmed": "Email confirmed",
        "yes": "Yes",
        "templates": "Templates (3)",
        "tpl_1": "Top 10 worst teachers",
        "tpl_1_state": "public · 5 reports",
        "tpl_2": "My favorite games",
        "tpl_2_state": "private",
        "tpl_3": "Series 2025",
        "tpl_3_state": "public",
        "open": "Open",
        "images": "Uploaded images (14)",
        "hide_all": "Hide all their images",
        "history": "Moderation history",
        "history_1": "Oct 28 · Nina hid the image “teacher.jpg”: harassment",
        "ban_title": "Ban this account",
        "ban_until": "Temporarily, until",
        "ban_forever": "Permanently",
        "ban_end": "End of the ban",
        "ban_reason": "Reason (shown to the person)",
        "ban_reason_value": "Repeated harassment",
        "ban_hint": "The account is signed out everywhere; its public templates leave "
        "the public templates while the ban lasts.",
        "ban": "Ban",
        "log_title": "Moderation log",
        "log_intro": "Every action: who, when, what and why. No entry can be edited or deleted.",
        "target": "Target",
        "target_hint": "Template, image, account…",
        "super_admin": "Super admin",
        "all": "All",
        "when": "When",
        "who": "Who",
        "action": "Action",
        "why": "Reason",
        "log_1": "Oct 31 18:42|Nina|Hide|Template “Top 10 worst teachers”|Harassment",
        "log_2": "Oct 31 18:40|Nina|Ban until Nov 15|Account Max|Repeated harassment",
        "log_3": "Oct 30 21:05|Samuel|Dismiss|Nickname “Lou”|No breach",
        "log_4": "Oct 29 09:12|Samuel|Delete|Image “capture.png”|Sexual content",
        "uploads_intro": "Uploaded images, newest first, to spot a problem before anyone "
        "reports it.",
        "author": "Author",
        "author_hint": "Name or email",
        "since": "Since",
        "status": "Status",
        "visible": "Visible",
        "up_1": "5 min ago|1 template",
        "up_2": "12 min ago|2 templates",
        "up_3": "1 h ago|1 template · 3 games",
        "up_4": "2 h ago|1 template",
        "up_5": "yesterday|4 games",
        "up_6": "yesterday|hidden",
    },
    "fr": {
        "public": "Modèles publics",
        "public_intro": "Trouvez une tier list à jouer avec vos amis, ou une idée à reprendre.",
        "search": "Rechercher un modèle",
        "sort": "Trier par",
        "most_liked": "Les plus aimés",
        "by": "par {owner} · {count} éléments",
        "lineage": "par Camille · copié de « Chips de l'apéro » par Noé",
        "items": "Éléments (12)",
        "start_room": "Créer une salle avec ce modèle",
        "like": "J'aime · 128",
        "favorite": "Favori",
        "copy": "Copier dans mes modèles",
        "copy_hint": "Votre copie est privée ; elle indique de quel modèle elle vient.",
        "report_link": "Signaler ce modèle",
        "visibility": "Visibilité",
        "private": "Privé : vous seul pouvez lancer une salle avec",
        "public_choice": "Public : tout le monde le trouve et peut le jouer",
        "allow_copies": "Autoriser les copies de ce modèle",
        "tags_field": "Tags (5 au plus)",
        "add_tag": "Ajouter un tag",
        "tags_hint": "Un mot ou une courte expression : on trouve votre modèle par ses tags.",
        "public_since": "Public depuis le 31 octobre 2026 · 128 j'aime",
        "other_states": "Autres états",
        "unconfirmed": "Confirmez votre adresse e-mail pour rendre un modèle public.",
        "hidden": "Masqué par la modération : images d'une autre personne publiées sans accord.",
        "hidden_hint": "Vous pouvez encore le modifier, mais plus le rendre public.",
        "report_title": "Signaler ce modèle",
        "report_intro": "Votre signalement est anonyme : la personne signalée ne saura pas "
        "qui l'a envoyé.",
        "reason": "Motif",
        "reasons": "Contenu illégal|Contenu sexuel|Violence ou haine|Harcèlement|Spam|Autre",
        "details": "Précisions (facultatif)",
        "send": "Envoyer le signalement",
        "moderation": "Modération",
        "reports": "Signalements",
        "uploads": "Derniers envois",
        "log": "Journal",
        "reports_intro": "Les signalements ouverts, regroupés par contenu, les plus signalés "
        "d'abord. Chaque décision est écrite au journal.",
        "kind_template": "Modèle",
        "kind_image": "Image",
        "kind_nickname": "Pseudo",
        "report_1": "Top 10 des pires profs",
        "report_2": "image de la tuile « Barbecue »",
        "report_3": "« xX_spam_Xx » dans la salle K7P2QX",
        "from": "de {owner} · {count} signalements",
        "from_one": "de {owner} · 1 signalement",
        "guest": "invité",
        "harassment": "Harcèlement ×4",
        "other": "Autre ×1",
        "sexual": "Contenu sexuel ×2",
        "spam": "Spam ×1",
        "dismiss": "Classer sans suite",
        "hide": "Masquer",
        "delete": "Supprimer",
        "see_account": "Voir le compte",
        "open_reports": "3 signalements ouverts",
        "no_sanction": "aucune sanction",
        "display_name": "Nom affiché",
        "email": "E-mail",
        "created": "Compte créé le",
        "created_value": "2 septembre 2026",
        "confirmed": "E-mail confirmé",
        "yes": "Oui",
        "templates": "Modèles (3)",
        "tpl_1": "Top 10 des pires profs",
        "tpl_1_state": "public · 5 signalements",
        "tpl_2": "Mes jeux préférés",
        "tpl_2_state": "privé",
        "tpl_3": "Séries 2025",
        "tpl_3_state": "public",
        "open": "Ouvrir",
        "images": "Images envoyées (14)",
        "hide_all": "Masquer toutes ses images",
        "history": "Historique de modération",
        "history_1": "28 oct. · Nina a masqué l'image « prof.jpg » : harcèlement",
        "ban_title": "Bannir ce compte",
        "ban_until": "Temporairement, jusqu'au",
        "ban_forever": "Définitivement",
        "ban_end": "Fin du bannissement",
        "ban_reason": "Motif (visible par la personne)",
        "ban_reason_value": "Harcèlement répété",
        "ban_hint": "Le compte est déconnecté partout ; ses modèles publics quittent les "
        "modèles publics le temps du bannissement.",
        "ban": "Bannir",
        "log_title": "Journal de modération",
        "log_intro": "Chaque action : qui, quand, quoi et pourquoi. Aucune entrée ne se modifie "
        "ni ne se supprime.",
        "target": "Cible",
        "target_hint": "Modèle, image, compte…",
        "super_admin": "Super admin",
        "all": "Tous",
        "when": "Quand",
        "who": "Qui",
        "action": "Action",
        "why": "Motif",
        "log_1": "31 oct. 18:42|Nina|Masquer|Modèle « Top 10 des pires profs »|Harcèlement",
        "log_2": "31 oct. 18:40|Nina|Bannir jusqu'au 15 nov.|Compte Max|Harcèlement répété",
        "log_3": "30 oct. 21:05|Samuel|Classer sans suite|Pseudo « Lou »|Pas d'infraction",
        "log_4": "29 oct. 09:12|Samuel|Supprimer|Image « capture.png »|Contenu sexuel",
        "uploads_intro": "Les images envoyées, des plus récentes aux plus anciennes, pour "
        "repérer un problème avant qu'on le signale.",
        "author": "Auteur",
        "author_hint": "Nom ou e-mail",
        "since": "Depuis le",
        "status": "Statut",
        "visible": "Visibles",
        "up_1": "il y a 5 min|1 modèle",
        "up_2": "il y a 12 min|2 modèles",
        "up_3": "il y a 1 h|1 modèle · 3 parties",
        "up_4": "il y a 2 h|1 modèle",
        "up_5": "hier|4 parties",
        "up_6": "hier|masquée",
    },
}

ITEMS: dict[str, list[str]] = {
    "en": ["Plain", "Paprika", "Chicken", "Onion", "Vinegar", "Cheese", "Chili", "Tomato",
           "Curry", "Bacon", "Mustard", "Barbecue"],
    "fr": ["Nature", "Paprika", "Poulet", "Oignon", "Vinaigre", "Fromage", "Piment", "Tomate",
           "Curry", "Bacon", "Moutarde", "Barbecue"],
}  # fmt: skip
TEMPLATE_NAME: dict[str, str] = {"en": "Chips tier list", "fr": "Tier list des chips"}
CHIP_ART: dict[str, str] = {"Barbecue": "#C2492E", "Paprika": "#FF8A2A", "Curry": "#FFC22E"}
# Modèles publics d'exemple : nom, propriétaire, tags, éléments, j'aime, couleur de l'aperçu
PUBLIC: dict[str, list[tuple[str, str, list[str], int, int, str]]] = {
    "en": [
        ("Chips tier list", "Camille", ["snacks", "party"], 12, 128, "#C2492E"),
        ("Best Christmas movies", "Noé", ["movies", "holidays"], 24, 96, "#5B7CFA"),
        ("First generation Pokémon", "Inès", ["video games"], 32, 87, "#FFC22E"),
        ("French cheeses", "Lou", ["food", "cheese"], 20, 64, "#D4B483"),
        ("Anime openings", "Sam", ["anime", "music"], 30, 51, "#A78BFA"),
        ("Grandma's desserts", "Alex", ["food"], 16, 33, "#F06BD0"),
    ],
    "fr": [
        ("Tier list des chips", "Camille", ["apéro", "snacks"], 12, 128, "#C2492E"),
        ("Meilleurs films de Noël", "Noé", ["films", "fêtes"], 24, 96, "#5B7CFA"),
        ("Pokémon de la 1re génération", "Inès", ["jeux vidéo"], 32, 87, "#FFC22E"),
        ("Fromages français", "Lou", ["cuisine", "fromage"], 20, 64, "#D4B483"),
        ("Openings d'anime", "Sam", ["anime", "musique"], 30, 51, "#A78BFA"),
        ("Desserts de grand-mère", "Alex", ["cuisine"], 16, 33, "#F06BD0"),
    ],
}
FILTER_TAGS: dict[str, list[str]] = {
    "en": ["food", "movies", "video games", "music", "party", "anime"],
    "fr": ["cuisine", "films", "jeux vidéo", "musique", "apéro", "anime"],
}
TEMPLATE_TAGS: dict[str, list[str]] = {"en": ["snacks", "party"], "fr": ["apéro", "snacks"]}


def c(t: Translator, key: str, **values: object) -> str:
    text: str = COPY[t.lang][key]
    for name, value in values.items():
        text = text.replace("{" + name + "}", str(value))
    return text


def h1(svg: Svg, x, y, text, size=32) -> None:
    svg.text(x, y, text, size, 900, INK, HEAD, stretch=125)


def h2(svg: Svg, x, y, text, size=20) -> None:
    svg.text(x, y, text, size, 900, INK, HEAD, stretch=115)


def public_header(svg: Svg, t: Translator, user: str | None) -> None:
    header(svg, t, user, ((c(t, "public"), None),))


def moderation_header(svg: Svg, t: Translator) -> None:
    header(svg, t, "Nina", ((c(t, "public"), None), (c(t, "moderation"), "3")))


def select(svg: Svg, x, y, w, label, value) -> None:
    """Liste déroulante : intitulé au-dessus, valeur et chevron dans le champ."""
    svg.text(x, y, label, 14, 600)
    svg.rect(x, y + 8, w, 40, CARD, INPUT, rx=8)
    svg.text(x + 12, y + 33, value, 14, 400)
    svg.add(
        f'<path d="M{x + w - 24} {y + 25}l5 5 5-5" fill="none" stroke="{MUTED_FG}" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
    )


def icon_button(svg: Svg, x, y, label, name, variant="outline", w=None, h=32) -> float:
    """Bouton avec une icône devant son libellé."""
    w = w or round(text_width(label) + 50)
    fill, stroke, color = {
        "outline": (CARD, BORDER, INK),
        "secondary": (MUTED, None, INK),
    }[variant]
    svg.rect(x, y, w, h, fill, stroke, rx=10)
    left: float = x + (w - text_width(label) - 22) / 2
    icon(svg, left, y + (h - 16) / 2, name, 16, color)
    svg.text(left + 22, y + h / 2 + 5, label, 14, 500, color)
    return w


def alert(svg: Svg, x, y, w, h, fill, line) -> None:
    """Encadré d'alerte : fond léger, bordure et pastille « ! » de la même couleur."""
    svg.rect(x, y, w, h, fill, line, rx=16, sw=1.5)
    svg.add(f'<circle cx="{x + 27}" cy="{y + 27}" r="11" fill="{line}"/>')
    svg.text(x + 27, y + 32, "!", 13, 800, "#FFFFFF", anchor="middle")


def moderation_nav(svg: Svg, t: Translator, current: str) -> None:
    """Menu de l'espace de modération, à gauche."""
    for index, key in enumerate(("reports", "uploads", "log")):
        y: float = 84 + index * 44
        if key == current:
            svg.rect(32, y, 180, 36, MUTED, rx=10)
        svg.text(46, y + 23, c(t, key), 14, 600 if key == current else 500,
                 INK if key == current else MUTED_FG)  # fmt: skip
        if key == "reports":
            tag(svg, 176, y + 8, "3", PRIMARY, "#FFFFFF")


# --- Écrans -------------------------------------------------------------------------------------


def marketplace(t: Translator) -> Svg:
    svg = Svg(c(t, "public"), 960, 860)
    public_header(svg, t, None)
    h1(svg, 32, 108, c(t, "public"))
    svg.text(32, 136, c(t, "public_intro"), 15, 400, MUTED_FG)
    svg.text(32, 176, c(t, "search"), 14, 600)
    svg.rect(32, 184, 560, 40, CARD, INPUT, rx=8)
    icon(svg, 44, 196, "search", 16, MUTED_FG)
    svg.text(68, 209, FILTER_TAGS[t.lang][0], 14, 400)
    select(svg, 616, 176, 312, c(t, "sort"), c(t, "most_liked"))
    x: float = 32 + text_width("Tags :", 13, 600) + 10
    svg.text(32, 262, "Tags :" if t.lang == "fr" else "Tags:", 13, 600)
    for index, label in enumerate(FILTER_TAGS[t.lang]):
        selected: bool = index == 0
        x += (
            tag(svg, x, 248, label, INK if selected else MUTED, "#F4F5FA" if selected else MUTED_FG)
            + 6
        )
    for index, (name, owner, tags, tiles, likes, color) in enumerate(PUBLIC[t.lang]):
        col, line = index % 3, index // 3
        cx, cy = 32 + col * 304, 288 + line * 246
        svg.rect(cx, cy, 288, 230, CARD, BORDER, rx=16)
        svg.rect(cx + 10, cy + 10, 268, 120, color, rx=10)
        svg.text(cx + 14, cy + 156, name, 15, 600)
        svg.text(cx + 14, cy + 178, c(t, "by", owner=owner, count=tiles), 13, 400, MUTED_FG)
        tx: float = cx + 14
        for label in tags:
            tx += tag(svg, tx, cy + 194, label) + 6
        icon(svg, cx + 244 - text_width(str(likes), 13, 600), cy + 196, "heart", 16, PRIMARY)
        svg.text(cx + 274, cy + 209, str(likes), 13, 600, PRIMARY, anchor="end")
    label: str = t("history.more")
    button(svg, 480 - button_width(label) / 2, 794, label, "outline")
    return svg


def template_page(t: Translator) -> Svg:
    items: list[str] = ITEMS[t.lang]
    svg = Svg(TEMPLATE_NAME[t.lang], 960, 640)
    public_header(svg, t, "Alex")
    svg.text(32, 92, "← " + c(t, "public"), 14, 500, MUTED_FG)
    h1(svg, 32, 136, TEMPLATE_NAME[t.lang], 30)
    svg.text(32, 162, c(t, "lineage"), 14, 400, MUTED_FG)
    x: float = 32
    for label in TEMPLATE_TAGS[t.lang]:
        x += tag(svg, x, 176, label) + 6
    h2(svg, 32, 232, "Tiers", 18)
    for index, (letter, color) in enumerate(TIERS):
        svg.rect(32 + index * 50, 246, 44, 44, color, rx=8)
        svg.text(54 + index * 50, 276, letter, 20, 900, INK, HEAD, anchor="middle", stretch=125)
    h2(svg, 32, 330, c(t, "items"), 18)
    for index, item in enumerate(items):
        col, line = index % 6, index // 6
        x, y = 32 + col * 96, 344 + line * 100
        svg.rect(x, y, 88, 92, CARD, BORDER, rx=10)
        svg.rect(x + 6, y + 6, 76, 56, CHIP_ART.get(item, MUTED), rx=6)
        svg.text(x + 44, y + 80, item, 12, 600, INK, anchor="middle")
    # Actions
    panel(svg, 640, 104, 288, 290)
    button(svg, 660, 124, c(t, "start_room"), "default", h=40, w=248)
    like_w: float = icon_button(svg, 660, 176, c(t, "like"), "heart")
    icon_button(svg, 660 + like_w + 8, 176, c(t, "favorite"), "star")
    icon_button(svg, 660, 220, c(t, "copy"), "copy", "secondary", w=248)
    wrap(svg, 660, 274, c(t, "copy_hint"), 240, 12, 16)
    icon(svg, 660, 350, "flag", 16, MUTED_FG)
    svg.text(684, 363, c(t, "report_link"), 13, 500, MUTED_FG)
    return svg


def publish(t: Translator) -> Svg:
    svg = Svg({"en": "Publish a template", "fr": "Publier un modèle"}[t.lang], 960, 580)
    header(svg, t, "Alex", ((c(t, "public"), None),))
    svg.text(32, 92, "← " + t("templates.editor.back"), 14, 500, MUTED_FG)
    field(svg, 32, 124, 520, t("templates.editor.name"), TEMPLATE_NAME[t.lang])
    label: str = t("rooms.create.open")
    button(svg, 928 - button_width(label), 132, label, "default", h=40)
    # Visibilité
    panel(svg, 32, 200, 440, 340)
    h2(svg, 56, 238, c(t, "visibility"))
    radio(svg, 56, 258, c(t, "private"))
    radio(svg, 56, 288, c(t, "public_choice"), True)
    checkbox(svg, 56, 330, c(t, "allow_copies"), False)
    svg.text(56, 384, c(t, "tags_field"), 14, 600)
    svg.rect(56, 392, 392, 40, CARD, INPUT, rx=8)
    x: float = 64
    for value in TEMPLATE_TAGS[t.lang]:
        w: float = round(text_width(value, 13) + 34)
        svg.rect(x, 399, w, 26, MUTED, rx=13)
        svg.text(x + 10, 416, value, 13, 400)
        svg.text(x + w - 14, 416, "✕", 11, 600, MUTED_FG, anchor="middle")
        x += w + 6
    svg.text(x + 4, 417, c(t, "add_tag"), 14, 400, INPUT)
    wrap(svg, 56, 452, c(t, "tags_hint"), 390, 12, 16)
    dot(svg, 64, 503)
    svg.text(78, 508, c(t, "public_since"), 13, 400, MUTED_FG)
    # Autres états
    h2(svg, 496, 238, c(t, "other_states"), 18)
    alert(svg, 496, 256, 432, 120, WARNING_BG, WARNING_LINE)
    wrap(svg, 548, 280, c(t, "unconfirmed"), 360, 14, 20, INK, 600)
    button(svg, 548, 326, t("account.verification.resend"), "outline")
    alert(svg, 496, 392, 432, 120, DANGER_BG, DESTRUCTIVE)
    y: float = wrap(svg, 548, 416, c(t, "hidden"), 360, 14, 20, INK, 600)
    wrap(svg, 548, y + 4, c(t, "hidden_hint"), 360, 13, 18)
    return svg


def report(t: Translator) -> Svg:
    svg = Svg(c(t, "report_title"), 960, 620)
    public_header(svg, t, None)
    svg.rect(0, 0, 960, 620, "#140F2B", opacity=0.6)
    panel(svg, 230, 40, 500, 548)
    h2(svg, 258, 100, c(t, "report_title"), 24)
    wrap(svg, 258, 132, c(t, "report_intro"), 440, 14, 20)
    svg.text(258, 196, c(t, "reason"), 14, 600)
    for index, reason in enumerate(c(t, "reasons").split("|")):
        radio(svg, 258, 210 + index * 30, reason, index == 1)
    svg.text(258, 412, c(t, "details"), 14, 600)
    svg.rect(258, 420, 444, 88, CARD, INPUT, rx=8)
    send: str = c(t, "send")
    send_w: float = button_width(send)
    button(svg, 702 - send_w, 532, send)
    cancel: str = t("rooms.settings.cancel")
    button(svg, 702 - send_w - 8 - button_width(cancel), 532, cancel, "outline")
    return svg


def reports(t: Translator) -> Svg:
    svg = Svg(c(t, "reports"), 960, 700)
    moderation_header(svg, t)
    moderation_nav(svg, t, "reports")
    h1(svg, 240, 108, c(t, "reports"), 30)
    wrap(svg, 240, 136, c(t, "reports_intro"), 680, 14, 20)
    cases = [
        (c(t, "kind_template"), c(t, "report_1"), c(t, "from", owner="Max", count=5),
         [c(t, "harassment"), c(t, "other")], "#9AA0B4"),
        (c(t, "kind_image"), c(t, "report_2"), c(t, "from", owner="Camille", count=2),
         [c(t, "sexual")], CHIP_ART["Barbecue"]),
        (c(t, "kind_nickname"), c(t, "report_3"), c(t, "from_one", owner=c(t, "guest")),
         [c(t, "spam")], None),
    ]  # fmt: skip
    for index, (kind, what, author, reasons, color) in enumerate(cases):
        y: float = 184 + index * 166
        panel(svg, 240, y, 688, 150)
        if color:
            svg.rect(260, y + 20, 64, 64, color, rx=10)
        else:
            svg.rect(260, y + 20, 64, 64, MUTED, rx=10)
            svg.text(292, y + 58, "Aa", 16, 700, MUTED_FG, anchor="middle")
        w: float = tag(svg, 340, y + 20, kind, INK, "#F4F5FA")
        svg.text(340 + w + 8, y + 35, what, 15, 600)
        svg.text(340, y + 60, author, 13, 400, MUTED_FG)
        x: float = 340
        for reason in reasons:
            x += tag(svg, x, y + 70, reason) + 6
        x = 260
        for label, variant in ((c(t, "dismiss"), "outline"), (c(t, "hide"), "secondary"),
                               (c(t, "delete"), "destructive")):  # fmt: skip
            x += button(svg, x, y + 104, label, variant) + 8
        svg.text(908, y + 125, c(t, "see_account"), 14, 600, PRIMARY, anchor="end")
    return svg


def account(t: Translator) -> Svg:
    svg = Svg({"en": "Account: Max", "fr": "Compte : Max"}[t.lang], 960, 760)
    moderation_header(svg, t)
    moderation_nav(svg, t, "reports")
    h1(svg, 240, 108, "Max", 30)
    w: float = tag(svg, 240, 124, c(t, "open_reports"), PRIMARY, "#FFFFFF")
    tag(svg, 246 + w, 124, c(t, "no_sanction"))
    # Informations
    panel(svg, 240, 160, 360, 128)
    facts: list[tuple[str, str]] = [
        (c(t, "display_name"), "Max"),
        (c(t, "email"), "max@exemple.fr"),
        (c(t, "created"), c(t, "created_value")),
        (c(t, "confirmed"), c(t, "yes")),
    ]
    for index, (label, value) in enumerate(facts):
        x, y = 260 + (index % 2) * 170, 190 + (index // 2) * 54
        svg.text(x, y, label, 12, 400, MUTED_FG)
        svg.text(x, y + 20, value, 14, 500)
    # Modèles, images, historique
    h2(svg, 240, 324, c(t, "templates"), 18)
    panel(svg, 240, 336, 360, 150)
    rows = [(c(t, "tpl_1"), c(t, "tpl_1_state"), True), (c(t, "tpl_2"), c(t, "tpl_2_state"), False),
            (c(t, "tpl_3"), c(t, "tpl_3_state"), False)]  # fmt: skip
    for index, (name, state, flagged) in enumerate(rows):
        y = 336 + index * 50
        if index:
            svg.add(f'<line x1="240" y1="{y}" x2="600" y2="{y}" stroke="{BORDER}"/>')
        svg.text(256, y + 22, name, 14, 500)
        tag(
            svg,
            256,
            y + 28,
            state,
            PRIMARY if flagged else MUTED,
            "#FFFFFF" if flagged else MUTED_FG,
        )
        svg.text(584, y + 30, c(t, "open"), 14, 600, PRIMARY, anchor="end")
    h2(svg, 240, 528, c(t, "images"), 18)
    button(svg, 240, 544, c(t, "hide_all"), "secondary")
    h2(svg, 240, 620, c(t, "history"), 18)
    panel(svg, 240, 634, 360, 48)
    svg.text(256, 663, c(t, "history_1"), 12, 400, INK)
    # Bannir
    panel(svg, 620, 160, 308, 420)
    h2(svg, 640, 196, c(t, "ban_title"))
    radio(svg, 640, 216, c(t, "ban_until"), True)
    radio(svg, 640, 246, c(t, "ban_forever"))
    field(svg, 640, 296, 180, c(t, "ban_end"), "15/11/2026")
    field(svg, 640, 368, 268, c(t, "ban_reason"), c(t, "ban_reason_value"))
    wrap(svg, 640, 436, c(t, "ban_hint"), 268, 12, 16)
    button(svg, 640, 524, c(t, "ban"), "destructive")
    return svg


def log(t: Translator) -> Svg:
    svg = Svg(c(t, "log_title"), 960, 580)
    moderation_header(svg, t)
    moderation_nav(svg, t, "log")
    h1(svg, 240, 108, c(t, "log_title"), 30)
    wrap(svg, 240, 136, c(t, "log_intro"), 680, 14, 20)
    field(svg, 240, 196, 260, c(t, "target"), "")
    svg.text(252, 229, c(t, "target_hint"), 14, 400, INPUT)
    select(svg, 524, 196, 180, c(t, "super_admin"), c(t, "all"))
    panel(svg, 240, 266, 688, 250)
    columns: list[float] = [256, 352, 416, 572, 796]
    for x, key in zip(columns, ("when", "who", "action", "target", "why"), strict=True):
        svg.text(x, 296, c(t, key), 12, 600, MUTED_FG)
    for index in range(4):
        y: float = 316 + index * 50
        svg.add(f'<line x1="240" y1="{y}" x2="928" y2="{y}" stroke="{BORDER}"/>')
        values: list[str] = c(t, f"log_{index + 1}").split("|")
        for x, value in zip(columns, values, strict=True):
            svg.text(x, y + 30, value, 12, 400, INK)
    return svg


def uploads(t: Translator) -> Svg:
    svg = Svg(c(t, "uploads"), 960, 800)
    moderation_header(svg, t)
    moderation_nav(svg, t, "uploads")
    h1(svg, 240, 108, c(t, "uploads"), 30)
    wrap(svg, 240, 136, c(t, "uploads_intro"), 680, 14, 20)
    field(svg, 240, 196, 220, c(t, "author"), "")
    svg.text(252, 229, c(t, "author_hint"), 14, 400, INPUT)
    field(svg, 476, 196, 150, c(t, "since"), "24/10/2026")
    select(svg, 642, 196, 150, c(t, "status"), c(t, "visible"))
    shots = [("#C2492E", "Camille"), ("#5B7CFA", "Noé"), ("#FFC22E", "Max"),
             ("#2EC4B6", "Inès"), ("#A78BFA", "Lou"), ("#9AA0B4", "Max")]  # fmt: skip
    for index, (color, author) in enumerate(shots):
        col, line = index % 3, index // 3
        x, y = 240 + col * 232, 272 + line * 256
        when, usage = c(t, f"up_{index + 1}").split("|")
        panel(svg, x, y, 216, 240)
        svg.rect(x + 8, y + 8, 200, 120, color, rx=10)
        svg.text(x + 12, y + 150, author, 13, 600)
        svg.text(x + 12, y + 172, when + " · " + usage, 12, 400, MUTED_FG)
        hide_w: float = button(svg, x + 12, y + 190, c(t, "hide"), "secondary")
        button(svg, x + 20 + hide_w, y + 190, c(t, "delete"), "destructive")
    return svg


SCREENS: dict[str, Screen] = {
    "marketplace": marketplace,
    "template-page": template_page,
    "publish": publish,
    "report": report,
    "moderation-reports": reports,
    "moderation-account": account,
    "moderation-log": log,
    "moderation-uploads": uploads,
}

if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    build(SCREENS, OUT_DIR)
