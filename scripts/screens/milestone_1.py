"""Wireframes du jalon 1 (docs/product/milestone-1/screens/), sur la charte « Le Plateau ».

Depuis la racine du dépôt, après pnpm install dans frontend/ :
    uv run --project backend python scripts/screens/milestone_1.py
Écrit les 8 écrans en anglais et en français ; décrits dans docs/product/milestone-1/screens.md.
"""

import os

from plateau import (
    BORDER,
    CARD,
    D_BG,
    D_BORDER,
    D_CARD,
    D_FG,
    D_MUTED_FG,
    D_ON_PRIMARY,
    D_PRIMARY,
    D_WARNING,
    HEAD,
    INK,
    INPUT,
    MUTED,
    MUTED_FG,
    PRIMARY,
    REPO_ROOT,
    SPOT,
    SUCCESS,
    TIERS,
    Screen,
    Svg,
    Translator,
    build,
    button,
    button_width,
    checkbox,
    chip,
    dot,
    field,
    head_width,
    header,
    panel,
    radio,
    segmented,
    tag,
    text_width,
    tier_rows,
    timer_pill,
    wrap,
)

OUT_DIR: str = os.path.join(REPO_ROOT, "docs", "product", "milestone-1", "screens")

# Les éléments du modèle d'exemple, dans la langue de l'écran
ITEMS: dict[str, list[str]] = {
    "en": [
        "Plain",
        "Paprika",
        "Chicken",
        "Onion",
        "Vinegar",
        "Cheese",
        "Chili",
        "Tomato",
        "Curry",
        "Bacon",
        "Mustard",
        "Barbecue",
    ],
    "fr": [
        "Nature",
        "Paprika",
        "Poulet",
        "Oignon",
        "Vinaigre",
        "Fromage",
        "Piment",
        "Tomate",
        "Curry",
        "Bacon",
        "Moutarde",
        "Barbecue",
    ],
}
TEMPLATE_NAME: dict[str, str] = {"en": "Chips tier list", "fr": "Tier list des chips"}
# Éléments avec une image : un aplat de couleur la représente
CHIP_ART: dict[str, str] = {"Barbecue": "#C2492E", "Paprika": "#FF8A2A", "Curry": "#FFC22E"}


def progress(svg: Svg, x, y, t: Translator, number=4, total=12) -> None:
    svg.text(
        x,
        y + 16,
        t("rooms.game.itemProgress", number=number, total=total),
        22,
        900,
        INK,
        HEAD,
        stretch=115,
    )
    bx = x + head_width(t("rooms.game.itemProgress", number=number, total=total), 22) + 24
    svg.rect(bx, y + 6, 240, 8, MUTED, rx=4)
    svg.rect(bx, y + 6, 240 * number / total, 8, INK, rx=4)


def status_list(svg: Svg, x, y, w, t: Translator, people) -> None:
    """people : (nom, clé du statut, en ligne)."""
    colors = {"placed": SUCCESS, "waiting": MUTED_FG, "disconnected": MUTED_FG}
    for index, (name, status, online) in enumerate(people):
        ry = y + index * 34
        dot(svg, x + 8, ry + 9, online)
        svg.text(x + 22, ry + 14, name, 14, 500)
        svg.text(
            x + w, ry + 14, t(f"rooms.game.status.{status}"), 13, 500, colors[status], anchor="end"
        )


# --- Écrans -------------------------------------------------------------------------------------


def template_editor(t: Translator) -> Svg:
    items = ITEMS[t.lang]
    svg = Svg({"en": "Template editor", "fr": "Éditeur de modèle"}[t.lang], 960, 660)
    header(svg, t, "Alex")
    svg.text(32, 92, "← " + t("templates.editor.back"), 14, 500, MUTED_FG)
    field(svg, 32, 124, 520, t("templates.editor.name"), TEMPLATE_NAME[t.lang])
    label = t("rooms.create.open")
    button(svg, 928 - button_width(label), 132, label, "default", h=40)
    # Tiers
    svg.text(32, 212, t("templates.editor.tiers"), 24, 900, INK, HEAD, stretch=115)
    for index, (letter, color) in enumerate(TIERS):
        ry = 228 + index * 54
        svg.rect(32, ry, 330, 46, CARD, BORDER, rx=10)
        svg.text(46, ry + 28, "⋮⋮", 14, 700, MUTED_FG)
        svg.rect(68, ry + 5, 36, 36, color, rx=8)
        svg.text(86, ry + 30, letter, 18, 900, INK, HEAD, anchor="middle", stretch=125)
        svg.rect(114, ry + 7, 196, 32, CARD, INPUT, rx=8)
        svg.text(124, ry + 28, letter, 14)
        svg.text(336, ry + 28, "✕", 14, 600, MUTED_FG, anchor="middle")
    button(svg, 32, 558, "+ " + t("templates.editor.addTier"), "secondary")
    # Tuiles
    svg.text(394, 212, t("templates.editor.tiles"), 24, 900, INK, HEAD, stretch=115)
    svg.text(
        928, 212, t("templates.editor.tileCount", count=12, max=32), 14, 500, MUTED_FG, anchor="end"
    )
    for index, item in enumerate(items):
        col, row = index % 6, index // 6
        x, y = 394 + col * 90, 228 + row * 100
        svg.rect(x, y, 82, 92, CARD, BORDER, rx=10)
        svg.rect(x + 6, y + 6, 70, 56, CHIP_ART.get(item, MUTED), rx=6)
        svg.text(x + 41, y + 80, item, 12, 600, INK, anchor="middle")
    panel(svg, 394, 444, 534, 196, "dashed")
    svg.rect(410, 460, 120, 120, "none", BORDER, rx=10, dash=True, sw=2)
    wrap(svg, 422, 508, t("templates.editor.image.hint"), 96, 12, 16, weight=500)
    field(svg, 546, 476, 366, t("templates.editor.newTileText"), "")
    wrap(svg, 546, 548, t("templates.editor.newTileHint"), 360, 12, 16)
    button(svg, 546, 588, t("templates.editor.addTile"), "default")
    return svg


def room_settings(t: Translator) -> Svg:
    svg = Svg(t("rooms.settings.dialogTitle"), 960, 640)
    header(svg, t, "Alex")
    svg.rect(0, 0, 960, 640, "#140F2B", opacity=0.6)
    panel(svg, 220, 40, 520, 584)
    svg.text(248, 100, t("rooms.settings.dialogTitle"), 24, 900, INK, HEAD, stretch=115)
    svg.text(248, 140, t("rooms.settings.itemOrder.label"), 14, 600)
    segmented(
        svg,
        248,
        152,
        [t("rooms.settings.itemOrder.template"), t("rooms.settings.itemOrder.random")],
        1,
    )
    svg.text(248, 224, t("rooms.settings.autoAdvance.label"), 14, 600)
    radio(svg, 248, 238, t("rooms.settings.autoAdvance.none"))
    radio(svg, 248, 266, t("rooms.settings.autoAdvance.timer"), True)
    radio(svg, 248, 294, t("rooms.settings.autoAdvance.everyone_placed"))
    field(svg, 248, 346, 200, t("rooms.settings.timerSeconds"), "30")
    panel(svg, 248, 412, 464, 40, "muted")
    svg.text(264, 437, t("rooms.settings.manualNote"), 13, 400, MUTED_FG)
    field(svg, 248, 484, 200, t("rooms.settings.cooldownSeconds"), "60")
    checkbox(svg, 480, 494, t("rooms.settings.adminPlays"))
    checkbox(svg, 248, 548, t("rooms.settings.lateArrivals"))
    submit = t("rooms.settings.submit")
    sw = button_width(submit)
    button(svg, 712 - sw, 584, submit)
    cancel = t("rooms.settings.cancel")
    button(svg, 712 - sw - 8 - button_width(cancel), 584, cancel, "outline")
    return svg


def join(t: Translator) -> Svg:
    svg = Svg(t("rooms.join.title"), 960, 580)
    header(svg, t, None)
    svg.text(480, 116, t("rooms.join.title"), 32, 900, INK, HEAD, anchor="middle", stretch=125)
    svg.text(480, 146, t("home.joinRoom.code"), 14, 500, MUTED_FG, anchor="middle")
    svg.text(
        480,
        206,
        "K7P2QX",
        56,
        900,
        INK,
        HEAD,
        anchor="middle",
        stretch=150,
        extra=' letter-spacing="2"',
    )
    # Avec un compte
    panel(svg, 120, 244, 350, 300)
    svg.text(144, 282, t("rooms.join.withAccount"), 20, 900, INK, HEAD, stretch=115)
    wrap(svg, 144, 314, t("rooms.join.withAccountHint"), 300, 14, 22)
    button(svg, 144, 488, t("rooms.join.signIn"), "outline", h=36, w=302)
    # En invité
    panel(svg, 490, 244, 350, 300)
    svg.text(514, 282, t("rooms.join.asGuest"), 20, 900, INK, HEAD, stretch=115)
    field(svg, 514, 316, 302, t("rooms.join.nickname"), "Lou")
    wrap(svg, 514, 394, t("rooms.join.asGuestHint"), 300, 13, 20)
    button(svg, 514, 488, t("rooms.join.submit"), "default", h=36, w=302)
    return svg


def lobby(t: Translator) -> Svg:
    svg = Svg({"en": "Lobby", "fr": "Salle d'attente"}[t.lang], 960, 600)
    header(svg, t, "Alex")
    svg.text(32, 108, t("rooms.lobby.title", code="K7P2QX"), 32, 900, INK, HEAD, stretch=125)
    svg.text(32, 134, t("rooms.lobby.template", name=TEMPLATE_NAME[t.lang]), 14, 500, MUTED_FG)
    # Inviter
    panel(svg, 32, 156, 560, 148)
    svg.text(56, 186, t("rooms.lobby.code"), 14, 600)
    svg.text(56, 240, "K7P2QX", 40, 900, INK, HEAD, stretch=125, extra=' letter-spacing="1"')
    svg.text(330, 186, t("rooms.lobby.link"), 14, 600)
    svg.rect(330, 198, 238, 36, CARD, INPUT, rx=8)
    svg.text(342, 221, "tierlist.app/r/K7P2QX", 14, 400)
    button(svg, 330, 248, t("rooms.lobby.copyLink"), "outline")
    # Participants
    svg.text(32, 340, t("rooms.lobby.participants", count=3), 20, 900, INK, HEAD, stretch=115)
    panel(svg, 32, 352, 560, 150)
    people = [
        ("Alex", t("rooms.lobby.admin"), True),
        ("Sam", None, True),
        ("Lou", t("rooms.lobby.guest"), False),
    ]
    for index, (name, role, online) in enumerate(people):
        ry = 352 + index * 50
        if index:
            svg.add(f'<line x1="32" y1="{ry}" x2="592" y2="{ry}" stroke="{BORDER}"/>')
        dot(svg, 56, ry + 25, online)
        svg.text(72, ry + 30, name, 14, 600)
        if role:
            fill, color = (SPOT, INK) if index == 0 else (MUTED, MUTED_FG)
            tag(svg, 72 + text_width(name, 14, 600) + 12, ry + 15, role, fill, color)
        svg.text(
            568,
            ry + 30,
            t("rooms.lobby.online" if online else "rooms.lobby.offline"),
            13,
            500,
            MUTED_FG,
            anchor="end",
        )
    # Réglages et actions
    panel(svg, 616, 156, 312, 216)
    svg.text(640, 190, t("rooms.settings.title"), 20, 900, INK, HEAD, stretch=115)
    button(
        svg, 904 - button_width(t("rooms.settings.edit")), 168, t("rooms.settings.edit"), "outline"
    )
    lines = [
        t("rooms.settings.summary.itemOrder.random"),
        t("rooms.settings.summary.autoAdvance.timer", seconds=30),
        t("rooms.settings.summary.cooldown", seconds=60),
        t("rooms.settings.summary.adminPlays"),
        t("rooms.settings.summary.lateArrivalsAllowed"),
    ]
    for index, line in enumerate(lines):
        svg.text(640, 230 + index * 28, "• " + line, 13, 400, INK)
    button(svg, 616, 388, t("rooms.lobby.start.submit"), "default", h=40, w=312)
    button(svg, 616, 438, t("rooms.lobby.close.open"), "destructive", h=36, w=312)
    # Parties passées
    svg.text(32, 538, t("rooms.lobby.pastGames.title", count=1), 20, 900, INK, HEAD, stretch=115)
    panel(svg, 32, 552, 896, 40)
    svg.text(
        56,
        577,
        TEMPLATE_NAME[t.lang] + " — " + t("rooms.lobby.pastGames.players_other", count=3),
        14,
        500,
    )
    svg.text(904, 577, t("rooms.lobby.pastGames.open"), 14, 600, PRIMARY, anchor="end")
    return svg


def round_player(t: Translator) -> Svg:
    items = ITEMS[t.lang]
    svg = Svg(
        {"en": "Round, participant view", "fr": "Manche, vue du participant"}[t.lang], 960, 560
    )
    header(svg, t, "Sam")
    progress(svg, 32, 78, t)
    timer_pill(svg, 848, 74, "0:18")
    # Carte de l'élément en cours, posée de biais
    svg.add('<g transform="rotate(-2 120 220)">')
    svg.rect(32, 134, 176, 190, CARD, PRIMARY, rx=16, sw=2)
    svg.rect(46, 148, 148, 128, CHIP_ART["Barbecue"], rx=10)
    svg.text(120, 304, items[11], 16, 700, INK, anchor="middle")
    svg.add("</g>")
    wrap(svg, 32, 360, t("rooms.game.dock"), 176, 12, 17)
    # Plateau du participant
    svg.text(232, 150, t("rooms.game.board"), 20, 900, INK, HEAD, stretch=115)
    tier_rows(
        svg,
        232,
        164,
        476,
        [[items[1]], [items[0], items[2]], [items[3]], [], [], []],
        row_h=56,
        slot=(1, 0),
        art=CHIP_ART,
    )
    # Qui a placé
    panel(svg, 728, 134, 200, 172)
    svg.text(748, 164, t("rooms.game.placedCount_other", placed=2, count=3), 14, 600)
    status_list(
        svg,
        748,
        182,
        160,
        t,
        [
            ("Alex", "placed", True),
            (t("rooms.game.nameYou", name="Sam"), "waiting", True),
            ("Lou", "placed", True),
        ],
    )
    return svg


def round_admin(t: Translator) -> Svg:
    items = ITEMS[t.lang]
    svg = Svg({"en": "Round, host view", "fr": "Manche, vue de l'hôte"}[t.lang], 960, 500)
    header(svg, t, "Alex")
    progress(svg, 32, 78, t)
    timer_pill(svg, 848, 74, "0:18")
    svg.add('<g transform="rotate(-2 120 220)">')
    svg.rect(32, 134, 176, 190, CARD, BORDER, rx=16)
    svg.rect(46, 148, 148, 128, CHIP_ART["Barbecue"], rx=10)
    svg.text(120, 304, items[11], 16, 700, INK, anchor="middle")
    svg.add("</g>")
    # Commandes de l'hôte, bordées de projecteur
    svg.rect(232, 134, 696, 330, CARD, SPOT, rx=16, sw=2)
    svg.text(256, 170, t("rooms.game.hostControls"), 20, 900, INK, HEAD, stretch=115)
    svg.text(256, 204, t("rooms.game.placedCount_other", placed=2, count=3), 14, 600)
    status_list(
        svg,
        256,
        222,
        360,
        t,
        [
            ("Alex", "placed", True),
            ("Sam", "waiting", True),
            ("Lou", "placed", True),
            ("Max", "disconnected", False),
        ],
    )
    button(svg, 660, 216, t("rooms.game.next"), "default", h=40, w=244)
    svg.text(660, 280, t("rooms.game.auto.timer", seconds=30), 13, 400, MUTED_FG)
    checkbox(svg, 660, 302, t("rooms.game.lateArrivals"))
    panel(svg, 256, 380, 648, 60, "muted")
    svg.text(
        276,
        415,
        {
            "en": "A host who plays also has their own tier list (screen 5).",
            "fr": "Un hôte qui joue a aussi sa propre tier list (écran 5).",
        }[t.lang],
        13,
        400,
        MUTED_FG,
    )
    return svg


def cooldown(t: Translator) -> Svg:
    items = ITEMS[t.lang]
    svg = Svg(t("rooms.game.cooldown.title"), 960, 600)
    header(svg, t, "Lou")
    # Le plateau sombre, quel que soit le thème
    svg.rect(24, 72, 912, 512, D_BG, D_WARNING, rx=16, sw=2, opacity=None)
    svg.text(48, 116, t("rooms.game.cooldown.title"), 26, 900, D_FG, HEAD, stretch=115)
    svg.text(912, 120, "0:42", 40, 900, D_WARNING, HEAD, anchor="end")
    svg.text(48, 144, t("rooms.game.cooldown.hint"), 14, 400, D_MUTED_FG)
    rows = [
        [items[1], items[5]],
        [items[0], items[9], items[2]],
        [items[3], items[8]],
        [items[6], items[7]],
        [items[10]],
        [],
    ]
    tier_rows(svg, 48, 164, 600, rows, row_h=60, dark=True, art=CHIP_ART)
    # Éléments manqués
    svg.rect(668, 164, 244, 250, D_CARD, D_BORDER, rx=16)
    svg.text(688, 194, t("rooms.game.cooldown.missed"), 16, 700, D_FG)
    for index, item in enumerate((items[4], items[11])):
        ry = 214 + index * 66
        width = chip(svg, 688, ry, item, 52, dark=True, art=CHIP_ART.get(item))
        tag(svg, 688 + width + 8, ry + 16, t("rooms.game.cooldown.absent"), D_PRIMARY, D_ON_PRIMARY)
    button(svg, 668, 432, t("rooms.game.cooldown.end.open"), "outline", h=40, w=244, dark=True)
    return svg


def results(t: Translator) -> Svg:
    items = ITEMS[t.lang]
    svg = Svg(t("results.title", name=TEMPLATE_NAME[t.lang]), 960, 620)
    header(svg, t, "Alex")
    svg.text(
        32, 108, t("results.title", name=TEMPLATE_NAME[t.lang]), 30, 900, INK, HEAD, stretch=125
    )
    segmented(
        svg,
        32,
        128,
        [t("results.tabs.median"), t("results.tabs.overall"), t("results.tabs.players")],
        0,
    )
    checkbox(svg, 400, 140, t("results.includeAbsentVotes"))
    label = t("rooms.lobby.copyLink")
    button(svg, 928 - button_width(label), 132, label, "outline")
    svg.text(
        928 - button_width(label) - 12,
        153,
        t("results.publicLink"),
        13,
        500,
        MUTED_FG,
        anchor="end",
    )
    rows = [
        [items[1], items[11]],
        [items[0], items[2], items[9]],
        [items[3], items[5]],
        [items[8], items[7]],
        [items[6], items[10]],
        [items[4]],
    ]
    tier_rows(svg, 32, 188, 580, rows, row_h=56, art=CHIP_ART)
    # Votes de l'élément choisi
    panel(svg, 636, 188, 292, 300)
    svg.text(656, 220, t("results.votes.title", item=items[11]), 16, 700)
    counts = [2, 1, 0, 0, 0, 0]
    for index, (letter, color) in enumerate(TIERS):
        ry = 240 + index * 30
        svg.text(656, ry + 15, letter, 15, 900, INK, HEAD, stretch=130)
        svg.rect(684, ry + 4, max(3, counts[index] * 80), 14, color, rx=4)
        svg.text(908, ry + 15, str(counts[index]), 13, 500, INK, anchor="end")
    ry = 240 + 6 * 30
    svg.text(656, ry + 15, t("results.votes.absent"), 13, 600, MUTED_FG)
    svg.add(
        '<pattern id="hatch" width="7" height="7" patternUnits="userSpaceOnUse" '
        f'patternTransform="rotate(45)"><rect width="3" height="7" fill="{MUTED_FG}"/></pattern>'
    )
    svg.rect(724, ry + 4, 80, 14, "url(#hatch)", MUTED_FG, rx=4)
    svg.text(908, ry + 15, "1", 13, 500, INK, anchor="end")
    play = t("results.playAgain")
    button(svg, 636, 506, play, "default", h=40, w=292)
    button(svg, 636, 556, t("results.backToRoom"), "outline", h=36, w=292)
    return svg


SCREENS: dict[str, Screen] = {
    "template-editor": template_editor,
    "room-settings": room_settings,
    "join": join,
    "lobby": lobby,
    "round-player": round_player,
    "round-admin": round_admin,
    "cooldown": cooldown,
    "results": results,
}

if __name__ == "__main__":
    build(SCREENS, OUT_DIR)
