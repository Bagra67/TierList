"""Fichiers image générés en mémoire, partagés par les tests unitaires et d'intégration."""

from io import BytesIO

from PIL import Image


def make_image_file(
    size: tuple[int, int],
    image_format: str,
    mode: str = "RGB",
    color: tuple[int, ...] = (200, 30, 30),
    **save_options: object,
) -> bytes:
    """Contenu d'un fichier image d'une seule couleur, dans ce format de Pillow (JPEG, PNG…)."""
    image: Image.Image = Image.new(mode, size, color)
    buffer: BytesIO = BytesIO()
    image.save(buffer, format=image_format, **save_options)
    return buffer.getvalue()
