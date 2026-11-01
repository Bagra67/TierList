"""Modèles du jeu de données : vides, en texte, avec images, pleins (32 tuiles) et supprimés.
Les images sont générées (une couleur, une forme, un numéro) et envoyées par le vrai service."""

import logging
import random
from collections.abc import Iterator
from dataclasses import dataclass
from io import BytesIO
from itertools import cycle

from PIL import Image as PillowImage
from PIL import ImageDraw
from sqlalchemy.orm import Session

from app.constants.templates import FREE_PLAN_MAX_TILES
from app.core.config import Settings
from app.models.image import Image
from app.models.template import Template
from app.models.user import User
from app.seed.sizes import SeedSize
from app.services.image_storage import ImageStorage
from app.services.images import ImageService
from app.services.templates import TemplateService

logger = logging.getLogger(__name__)

TEXT_THEMES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Fruits",
        (
            "Pomme",
            "Banane",
            "Fraise",
            "Mangue",
            "Kiwi",
            "Ananas",
            "Cerise",
            "Poire",
            "Litchi",
            "Figue",
        ),
    ),
    (
        "Pizzas",
        (
            "Margherita",
            "Reine",
            "4 fromages",
            "Calzone",
            "Hawaïenne",
            "Napolitaine",
            "Chorizo",
            "Végétarienne",
        ),
    ),
    (
        "Desserts",
        (
            "Tiramisu",
            "Crème brûlée",
            "Mousse au chocolat",
            "Tarte Tatin",
            "Paris-Brest",
            "Éclair",
            "Macaron",
        ),
    ),
    (
        "Fromages",
        (
            "Comté",
            "Brie",
            "Roquefort",
            "Camembert",
            "Reblochon",
            "Munster",
            "Chèvre",
            "Beaufort",
            "Tomme",
        ),
    ),
    (
        "Sports",
        (
            "Football",
            "Tennis",
            "Natation",
            "Escalade",
            "Rugby",
            "Handball",
            "Judo",
            "Basket",
            "Voile",
            "Ski",
        ),
    ),
    (
        "Saisons et fêtes",
        (
            "Printemps",
            "Été",
            "Automne",
            "Hiver",
            "Noël",
            "Halloween",
        ),
    ),
    (
        "Petits-déjeuners",
        (
            "Croissant",
            "Pain au chocolat",
            "Tartine",
            "Céréales",
            "Pancakes",
            "Yaourt",
            "Œufs brouillés",
        ),
    ),
    (
        "Jeux de société",
        (
            "Échecs",
            "Uno",
            "Monopoly",
            "Dixit",
            "Codenames",
            "Carcassonne",
            "Dobble",
            "Catan",
            "Taboo",
        ),
    ),
    (
        "Légumes",
        (
            "Carotte",
            "Courgette",
            "Brocoli",
            "Poireau",
            "Épinard",
            "Aubergine",
            "Radis",
            "Potiron",
        ),
    ),
)
WORD_POOL: tuple[str, ...] = tuple(word for _, words in TEXT_THEMES for word in words) + (
    "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche", "Plage", "Montagne",
    "Forêt", "Désert", "Volcan", "Rivière", "Lac", "Glacier", "Île", "Ville", "Village",
)  # fmt: skip
IMAGE_THEMES: tuple[str, ...] = (
    "Couleurs", "Formes", "Drapeaux imaginaires", "Pastilles", "Affiches", "Badges",
)  # fmt: skip
FULL_THEMES: tuple[str, ...] = (
    "Le grand classement", "Tout le menu", "Mots du quotidien", "Le marathon", "Tout ou rien",
    "La totale",
)  # fmt: skip
COLORS: tuple[tuple[int, int, int], ...] = (
    (212, 30, 91), (255, 194, 46), (46, 196, 182), (91, 124, 250), (123, 217, 74), (255, 138, 42),
    (29, 22, 64), (244, 245, 250),
)  # fmt: skip
SHAPES: tuple[str, ...] = ("circle", "square", "triangle")


@dataclass(frozen=True)
class SeedTemplates:
    # Modèles avec au moins une tuile : les parties et les salles en sont faites
    playable: list[Template]
    empty: list[Template]
    deleted: list[Template]


def create_templates(
    session: Session,
    settings: Settings,
    storage: ImageStorage,
    size: SeedSize,
    owners: list[User],
    rng: random.Random,
) -> SeedTemplates:
    templates: TemplateService = TemplateService(session, settings)
    images: ImageService = ImageService(session, settings, storage)
    # Les modèles sont répartis entre les joueurs, à tour de rôle
    owner_turns: Iterator[User] = cycle(owners)

    def next_owner() -> User:
        return next(owner_turns)

    created: list[int] = [0]
    total: int = (
        size.text_templates
        + size.image_templates
        + size.full_templates
        + size.empty_templates
        + size.deleted_templates
    )

    def log_created(template: Template) -> None:
        created[0] += 1
        logger.info(
            "Modèle %d/%d : %s (%d tuiles)", created[0], total, template.name, len(template.tiles)
        )

    def with_texts(owner: User, name: str, words: list[str]) -> Template:
        template: Template = templates.create(owner, name)
        for word in words:
            template = templates.add_tile(owner, template.id, word, None)
        log_created(template)
        return template

    playable: list[Template] = []
    for index in range(size.text_templates):
        theme, words = TEXT_THEMES[index % len(TEXT_THEMES)]
        playable.append(with_texts(next_owner(), theme, list(words)))
    for index in range(size.image_templates):
        # Un propriétaire par modèle à images : au plus 120 envois par heure et par compte
        owner: User = owners[index % len(owners)]
        template: Template = templates.create(owner, IMAGE_THEMES[index % len(IMAGE_THEMES)])
        for tile_number in range(1, size.image_tiles_per_template + 1):
            image: Image = images.upload(owner, BytesIO(_generated_image(tile_number, rng)))
            # Une tuile sur trois a aussi un texte
            text: str | None = f"Image {tile_number}" if tile_number % 3 == 0 else None
            template = templates.add_tile(owner, template.id, text, image.id)
            logger.info(
                "Image %d/%d envoyée (modèle %s)",
                tile_number,
                size.image_tiles_per_template,
                template.name,
            )
        log_created(template)
        playable.append(template)
    for index in range(size.full_templates):
        full_words: list[str] = rng.sample(WORD_POOL, FREE_PLAN_MAX_TILES)
        playable.append(with_texts(next_owner(), FULL_THEMES[index % len(FULL_THEMES)], full_words))

    empty: list[Template] = []
    for number in range(1, size.empty_templates + 1):
        empty_template: Template = templates.create(next_owner(), f"Brouillon {number}")
        log_created(empty_template)
        empty.append(empty_template)
    deleted: list[Template] = []
    for number in range(1, size.deleted_templates + 1):
        owner = next_owner()
        template = with_texts(owner, f"Ancien modèle {number}", rng.sample(WORD_POOL, 4))
        # Supprimé maintenant : la purge de nuit ne l'efface qu'après 30 jours
        templates.delete(owner, template.id)
        deleted.append(template)
    return SeedTemplates(playable=playable, empty=empty, deleted=deleted)


def _generated_image(number: int, rng: random.Random) -> bytes:
    """Une image de 640×480 : un fond, une forme et un numéro, en PNG ou en JPEG."""
    background: tuple[int, int, int] = rng.choice(COLORS)
    foreground: tuple[int, int, int] = rng.choice(
        [color for color in COLORS if color != background]
    )
    image: PillowImage.Image = PillowImage.new("RGB", (640, 480), background)
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(image)
    shape: str = rng.choice(SHAPES)
    box: tuple[int, int, int, int] = (170, 90, 470, 390)
    if shape == "circle":
        draw.ellipse(box, fill=foreground)
    elif shape == "square":
        draw.rectangle(box, fill=foreground)
    else:
        draw.polygon([(320, 90), (470, 390), (170, 390)], fill=foreground)
    draw.text((30, 30), str(number), fill=foreground, font_size=64)
    buffer: BytesIO = BytesIO()
    image.save(buffer, format="PNG" if number % 2 else "JPEG")
    return buffer.getvalue()
