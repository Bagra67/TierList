"""Kit de dessin des wireframes de docs/product/, sur l'identité visuelle « Le Plateau ».

Les couleurs, polices et rayons sont ceux de docs/technical/visual-identity.md ; les textes viennent
des traductions de l'application (frontend/src/i18n/locales). Chaque écran est dessiné en SVG, dans
chaque langue, avec Anybody et Geist embarquées en sous-ensembles : GitHub affiche un SVG comme une
image, sans charger de police web.

Prérequis : Node (pour lire les traductions .ts), les dépendances du frontend installées
(pnpm install : les polices viennent de @fontsource-variable) et uv (pyftsubset via uvx).
"""

import base64
import json
import os
import subprocess
import tempfile
from collections.abc import Callable
from xml.sax.saxutils import escape

REPO_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LANGUAGES: tuple[str, ...] = ("en", "fr")
FONTTOOLS: str = "fonttools[woff]==4.68.0"
FONTSOURCE: str = "frontend/node_modules/@fontsource-variable"
FONT_FILES: dict[str, str] = {
    "Anybody": f"{FONTSOURCE}/anybody/files/anybody-latin-wdth-normal.woff2",
    "Geist": f"{FONTSOURCE}/geist/files/geist-latin-wght-normal.woff2",
}

# Thème clair (équivalents hexadécimaux des tokens oklch de frontend/src/index.css)
BG, INK, CARD, BORDER = "#F4F5FA", "#1D1640", "#FFFFFF", "#D5D6E4"
MUTED, MUTED_FG, PRIMARY, ON_PRIMARY = "#E9EAF3", "#5E5878", "#D41E5B", "#FFFFFF"
SPOT, INPUT, SUCCESS, DESTRUCTIVE = "#FFC22E", "#8C88A6", "#168057", "#B32517"
# Plateau sombre des retouches finales, quel que soit le thème
D_BG, D_CARD, D_FG, D_BORDER, D_MUTED_FG = "#140F2B", "#1D1640", "#ECEAF6", "#3A3170", "#A49FBF"
D_PRIMARY, D_ON_PRIMARY, D_WARNING = "#FF5C8A", "#140F2B", "#FFC22E"
TIERS: list[tuple[str, str]] = [
    ("S", "#FF3B6B"),
    ("A", "#FF8A2A"),
    ("B", "#FFC22E"),
    ("C", "#7BD94A"),
    ("D", "#2EC4B6"),
    ("E", "#5B7CFA"),
]
HEAD: str = "Anybody"
SANS: str = "Geist"


# --- Traductions --------------------------------------------------------------------------------


def load_translations() -> dict[str, dict]:
    """Lit fr.ts et en.ts avec Node (les types sont retirés à la volée)."""
    script: str = (
        "Promise.all([import('./frontend/src/i18n/locales/fr.ts'),"
        "import('./frontend/src/i18n/locales/en.ts')])"
        ".then(([f, e]) => process.stdout.write(JSON.stringify({fr: f.fr, en: e.en})))"
    )
    completed: subprocess.CompletedProcess[str] = subprocess.run(
        ["node", "--experimental-strip-types", "--no-warnings", "-e", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(completed.stdout)


class Translator:
    def __init__(self, translations: dict[str, dict], lang: str) -> None:
        self.lang: str = lang
        self._messages: dict = translations[lang]

    def __call__(self, key: str, **values: object) -> str:
        node: object = self._messages
        for part in key.split("."):
            node = node[part]  # type: ignore[index]
        text: str = str(node)
        for name, value in values.items():
            text = text.replace("{{" + name + "}}", str(value))
        return text


# --- SVG ----------------------------------------------------------------------------------------


class Svg:
    def __init__(self, title: str, width: int, height: int, background: str = BG) -> None:
        self.title, self.width, self.height = title, width, height
        self.parts: list[str] = [f'<rect width="{width}" height="{height}" fill="{background}"/>']
        # Caractères écrits : le sous-ensemble des polices n'en garde que ceux-là
        self.chars: set[str] = set()

    def add(self, markup: str) -> None:
        self.parts.append(markup)

    def rect(
        self,
        x,
        y,
        w,
        h,
        fill="none",
        stroke=None,
        rx: float = 0,
        dash=False,
        sw: float = 1,
        opacity=None,
    ) -> None:
        attrs: str = f'x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"'
        if stroke:
            attrs += f' stroke="{stroke}" stroke-width="{sw}"'
        if dash:
            attrs += ' stroke-dasharray="6 5"'
        if opacity is not None:
            attrs += f' opacity="{opacity}"'
        self.add(f"<rect {attrs}/>")

    def text(
        self,
        x,
        y,
        s,
        size=14,
        weight=400,
        fill=INK,
        family=SANS,
        anchor="start",
        stretch=None,
        extra="",
    ) -> None:
        self.chars.update(s)
        style: str = f"font-family:{family};font-size:{size}px;font-weight:{weight}"
        if stretch:
            style += f";font-stretch:{stretch}%"
        self.add(
            f'<text x="{x}" y="{y}" fill="{fill}" text-anchor="{anchor}" style="{style}"{extra}>'
            f"{escape(s)}</text>"
        )

    def render(self, fonts_css: str) -> str:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" '
            f'viewBox="0 0 {self.width} {self.height}" role="img" '
            f'aria-label="{escape(self.title)}">\n'
            f"<title>{escape(self.title)}</title>\n<style>{fonts_css}text{{font-kerning:normal}}</style>\n"
            + "\n".join(self.parts)
            + "\n</svg>\n"
        )


# Largeurs estimées (pas de mesure réelle) : assez pour placer les éléments sans chevauchement
def text_width(s: str, size: float = 14, weight: int = 500) -> float:
    return len(s) * size * (0.56 if weight >= 600 else 0.53)


def head_width(s: str, size: float) -> float:
    return len(s) * size * 0.74


def wrap(svg: Svg, x, y, text, width, size=13, line_h=18, fill=MUTED_FG, weight=400) -> float:
    """Écrit un texte sur des lignes de largeur estimée ; renvoie le y de la ligne suivante."""
    line: str = ""
    for word in text.split(" "):
        candidate: str = (line + " " + word).strip()
        if line and text_width(candidate, size, weight) > width:
            svg.text(x, y, line, size, weight, fill)
            y += line_h
            line = word
        else:
            line = candidate
    if line:
        svg.text(x, y, line, size, weight, fill)
        y += line_h
    return y


# --- Pièces de l'interface ----------------------------------------------------------------------


def header(svg: Svg, t: Translator, user: str | None) -> None:
    """En-tête : logo (trois barres S, A, B), navigation, avatar ou « Connexion »."""
    svg.rect(0, 0, svg.width, 56, CARD)
    svg.add(f'<line x1="0" y1="56" x2="{svg.width}" y2="56" stroke="{BORDER}"/>')
    for index, (width, color) in enumerate(
        ((22, TIERS[0][1]), (16, TIERS[1][1]), (10, TIERS[2][1]))
    ):
        svg.rect(24, 17 + index * 8, width, 6, color, rx=1.5)
    svg.text(54, 36, "TierList", 20, 900, INK, HEAD, stretch=125)
    x: float = 190
    for key in ("nav.home", "nav.templates", "nav.history"):
        label: str = t(key)
        svg.text(x, 33, label, 14, 500, MUTED_FG)
        x += text_width(label) + 28
    if user is None:
        label = t("auth.login.title")
        button(svg, svg.width - 24 - button_width(label), 12, label, "outline")
    else:
        svg.add(f'<circle cx="{svg.width - 40}" cy="28" r="16" fill="{MUTED}"/>')
        svg.text(svg.width - 40, 33, user[0], 13, 600, INK, anchor="middle")


def button_width(label: str, size: int = 14) -> float:
    return round(text_width(label, size) + 28)


def button(svg: Svg, x, y, label, variant="default", h=32, w=None, dark=False) -> float:
    w = w or button_width(label)
    fills: dict[str, tuple[str, str | None, str]] = {
        "default": (D_PRIMARY if dark else PRIMARY, None, D_ON_PRIMARY if dark else ON_PRIMARY),
        "secondary": (MUTED, None, INK),
        "outline": (D_CARD if dark else BG, D_BORDER if dark else BORDER, D_FG if dark else INK),
        "destructive": ("#F6E4E3", None, DESTRUCTIVE),
    }
    fill, stroke, color = fills[variant]
    svg.rect(x, y, w, h, fill, stroke, rx=10)
    svg.text(x + w / 2, y + h / 2 + 5, label, 14, 500, color, anchor="middle")
    return w


def panel(svg: Svg, x, y, w, h, variant="solid", dark=False) -> None:
    """Les panneaux de panelVariants : plein, pointillé, atténué ; rayon 16."""
    if variant == "solid":
        svg.rect(x, y, w, h, D_CARD if dark else CARD, D_BORDER if dark else BORDER, rx=16)
    elif variant == "dashed":
        svg.rect(x, y, w, h, "none", D_BORDER if dark else BORDER, rx=16, dash=True, sw=2)
    elif variant == "muted":
        svg.rect(x, y, w, h, MUTED, rx=16)


def chip(svg: Svg, x, y, label, h=44, dark=False, current=False, art=None) -> float:
    """Puce d'un élément (texte, et image si art) ; renvoie sa largeur."""
    w: float = round(text_width(label) + 22 + (h if art else 0))
    stroke, sw = (PRIMARY, 2) if current else (D_BORDER if dark else BORDER, 1)
    svg.rect(x, y, w, h, D_CARD if dark else CARD, stroke, rx=8, sw=sw)
    tx: float = x + 11
    if art:
        svg.rect(x + 4, y + 4, h - 8, h - 8, art, rx=6)
        tx = x + h + 4
    svg.text(tx, y + h / 2 + 5, label, 14, 500, D_FG if dark else INK)
    return w


def tier_rows(svg: Svg, x, y, w, rows, row_h=56, dark=False, slot=None, art=None) -> float:
    """Lignes de tier S à E.

    rows : les éléments de chaque tier ; slot : (tier,) d'un emplacement en pointillés à la fin
    d'un tier ; art : couleur de l'image de certains éléments.
    """
    art = art or {}
    for index, (letter, color) in enumerate(TIERS):
        ry: float = y + index * (row_h + 6)
        svg.rect(x, ry, w, row_h, D_CARD if dark else CARD, D_BORDER if dark else BORDER, rx=10)
        svg.add(
            f'<path d="M{x + 10} {ry}h{62}v{row_h}h-62a10 10 0 0 1-10-10v-{row_h - 20}'
            f'a10 10 0 0 1 10-10z" fill="{color}"/>'
        )
        svg.text(
            x + 36, ry + row_h / 2 + 11, letter, 30, 900, INK, HEAD, anchor="middle", stretch=125
        )
        cx: float = x + 80
        for item in rows[index] if index < len(rows) else []:
            cx += chip(svg, cx, ry + 6, item, row_h - 12, dark=dark, art=art.get(item)) + 6
        if slot and slot[0] == index:
            svg.rect(cx, ry + 6, 120, row_h - 12, "none", PRIMARY, rx=8, dash=True, sw=2)
    return y + len(TIERS) * (row_h + 6)


def tag(svg: Svg, x, y, label, fill=MUTED, color=MUTED_FG) -> float:
    w: float = round(text_width(label, 12) + 16)
    svg.rect(x, y, w, 20, fill, rx=10)
    svg.text(x + w / 2, y + 14, label, 12, 500, color, anchor="middle")
    return w


def dot(svg: Svg, x, y, online=True) -> None:
    if online:
        svg.add(f'<circle cx="{x}" cy="{y}" r="5" fill="{SUCCESS}"/>')
    else:
        svg.add(
            f'<circle cx="{x}" cy="{y}" r="4" fill="none" stroke="{MUTED_FG}" stroke-width="2"/>'
        )


def field(svg: Svg, x, y, w, label, value, h=40) -> None:
    svg.text(x, y, label, 14, 600)
    svg.rect(x, y + 8, w, h, CARD, INPUT, rx=8)
    svg.text(x + 12, y + 8 + h / 2 + 5, value, 14, 400)


def checkbox(svg: Svg, x, y, label, checked=True, dark=False) -> None:
    if checked:
        svg.rect(x, y, 16, 16, D_PRIMARY if dark else PRIMARY, rx=4)
        stroke: str = D_ON_PRIMARY if dark else "#FFFFFF"
        svg.add(
            f'<path d="M{x + 4} {y + 8.5}l3 3 5-6" fill="none" stroke="{stroke}" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round"/>'
        )
    else:
        svg.rect(x, y, 16, 16, CARD, INPUT, rx=4, sw=1.5)
    svg.text(x + 26, y + 13, label, 14, 400, D_FG if dark else INK)


def radio(svg: Svg, x, y, label, checked=False) -> None:
    svg.add(
        f'<circle cx="{x + 8}" cy="{y + 8}" r="7.5" fill="{CARD}" '
        f'stroke="{PRIMARY if checked else INPUT}" stroke-width="1.5"/>'
    )
    if checked:
        svg.add(f'<circle cx="{x + 8}" cy="{y + 8}" r="4" fill="{PRIMARY}"/>')
    svg.text(x + 26, y + 13, label, 14, 400)


def timer_pill(svg: Svg, x, y, label, fill=SPOT, color=INK, size=24) -> None:
    """Minuteur en pastille, au projecteur."""
    w: float = round(text_width(label, size, 900) + 34)
    svg.rect(x, y, w, size + 16, fill, rx=(size + 16) / 2)
    svg.text(x + w / 2, y + size + 3, label, size, 900, color, HEAD, anchor="middle")


def segmented(svg: Svg, x, y, labels, selected=0) -> None:
    """Onglets en pilule, l'onglet choisi à l'encre."""
    widths: list[float] = [round(text_width(label) + 32) for label in labels]
    svg.rect(x, y, sum(widths) + 8, 40, MUTED, rx=20)
    cx: float = x + 4
    for index, (label, w) in enumerate(zip(labels, widths, strict=True)):
        if index == selected:
            svg.rect(cx, y + 4, w, 32, INK, rx=16)
        svg.text(
            cx + w / 2,
            y + 25,
            label,
            14,
            600,
            BG if index == selected else MUTED_FG,
            anchor="middle",
        )
        cx += w


# --- Construction -------------------------------------------------------------------------------

Screen = Callable[[Translator], Svg]


def subset_fonts(chars: str, out_dir: str) -> dict[str, str]:
    """Réduit chaque police aux caractères écrits (pyftsubset) ; renvoie le chemin des fichiers."""
    text_file: str = os.path.join(out_dir, "chars.txt")
    with open(text_file, "w", encoding="utf-8") as f:
        f.write(chars)
    subsets: dict[str, str] = {}
    for family, source in FONT_FILES.items():
        output: str = os.path.join(out_dir, f"{family}.woff2")
        subprocess.run(
            [
                "uvx",
                "--from",
                FONTTOOLS,
                "pyftsubset",
                os.path.join(REPO_ROOT, source),
                f"--text-file={text_file}",
                "--flavor=woff2",
                "--layout-features=*",
                f"--output-file={output}",
            ],
            check=True,
            capture_output=True,
        )
        subsets[family] = output
    return subsets


def fonts_css(subsets: dict[str, str]) -> str:
    css: str = ""
    for family, path in subsets.items():
        with open(path, "rb") as f:
            data: str = base64.b64encode(f.read()).decode()
        css += (
            f"@font-face{{font-family:{family};"
            f"src:url(data:font/woff2;base64,{data}) format('woff2');"
            "font-weight:100 900;font-stretch:50% 150%}"
        )
    return css


def build(screens: dict[str, Screen], out_dir: str) -> None:
    """Dessine chaque écran dans chaque langue : <nom>.<langue>.svg dans out_dir."""
    translations: dict[str, dict] = load_translations()
    for lang in LANGUAGES:
        t: Translator = Translator(translations, lang)
        # Premier passage : les caractères écrits, pour réduire les polices à ce qui sert
        chars: set[str] = set()
        for draw in screens.values():
            chars |= draw(t).chars
        with tempfile.TemporaryDirectory() as fonts_dir:
            css: str = fonts_css(subset_fonts("".join(sorted(chars)) + "0123456789", fonts_dir))
        for name, draw in screens.items():
            path: str = os.path.join(out_dir, f"{name}.{lang}.svg")
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(draw(t).render(css))
            print(os.path.relpath(path, REPO_ROOT))
