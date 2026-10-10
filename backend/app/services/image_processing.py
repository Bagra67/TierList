"""Compression des images des tuiles avec Pillow (docs/technical/images.md, « Processing »).

Le fichier reçu n'est jamais stocké : il est décodé puis réencodé en WebP, sans métadonnées. Le
réencodage neutralise aussi les fichiers forgés pour être à la fois une image et autre chose.
"""

from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageOps

from app.constants.images import (
    ACCEPTED_IMAGE_FORMATS,
    IMAGE_OUTPUT_MAX_SIDE_PX,
    IMAGE_WEBP_QUALITY,
)
from app.exceptions.images import ImageTooManyPixelsError, ImageUnsupportedFormatError

# Pillow signale un fichier invalide ou tronqué par l'une de ces exceptions
# (UnidentifiedImageError hérite d'OSError ; verify() lève SyntaxError sur un PNG corrompu)
_INVALID_IMAGE_ERRORS: tuple[type[Exception], ...] = (OSError, SyntaxError, ValueError)


@dataclass(frozen=True)
class CompressedImage:
    data: bytes
    width: int
    height: int


def compress_image(content: bytes, max_source_pixels: int) -> CompressedImage:
    """Vérifie l'image reçue puis la réencode en WebP, son plus grand côté à
    IMAGE_OUTPUT_MAX_SIDE_PX.

    Le format est reconnu d'après le contenu du fichier, jamais d'après son nom ou son type MIME,
    que le client choisit librement.
    """
    _verify(content, max_source_pixels)
    try:
        with Image.open(BytesIO(content), formats=ACCEPTED_IMAGE_FORMATS) as source:
            # Seule la première image d'un fichier animé (WebP, PNG) est gardée
            source.load()
            icc_profile: bytes | None = source.info.get("icc_profile")
            # Photo de téléphone : l'orientation est une métadonnée EXIF, appliquée aux pixels
            upright: Image.Image = ImageOps.exif_transpose(source)
            converted: Image.Image = _convert_mode(upright)
    except Image.DecompressionBombError as exc:
        raise ImageTooManyPixelsError from exc
    except _INVALID_IMAGE_ERRORS as exc:
        raise ImageUnsupportedFormatError from exc

    resized: Image.Image = _fit_to_output_size(converted)
    output: BytesIO = BytesIO()
    # Aucune métadonnée (EXIF, position GPS) n'est recopiée : seul le profil de couleur l'est,
    # sinon les photos en couleurs étendues (Display P3) seraient affichées ternes
    resized.save(
        output,
        format="WEBP",
        quality=IMAGE_WEBP_QUALITY,
        icc_profile=icc_profile,
        exif=b"",
        xmp=b"",
    )
    return CompressedImage(data=output.getvalue(), width=resized.width, height=resized.height)


def _verify(content: bytes, max_source_pixels: int) -> None:
    """Refuse un fichier qui n'est pas une image acceptée, ou dont l'image décodée serait trop
    grande. Ne lit que l'en-tête et la structure du fichier, sans décoder les pixels."""
    try:
        with Image.open(BytesIO(content), formats=ACCEPTED_IMAGE_FORMATS) as header:
            pixel_count: int = header.width * header.height
            if pixel_count > max_source_pixels:
                raise ImageTooManyPixelsError
            header.verify()
    except Image.DecompressionBombError as exc:
        raise ImageTooManyPixelsError from exc
    except _INVALID_IMAGE_ERRORS as exc:
        raise ImageUnsupportedFormatError from exc


def _convert_mode(image: Image.Image) -> Image.Image:
    """RGB, ou RGBA quand l'image a de la transparence (PNG, WebP), pour qu'elle la garde."""
    if image.has_transparency_data:
        return image.convert("RGBA")
    return image.convert("RGB")


def _fit_to_output_size(image: Image.Image) -> Image.Image:
    """Réduit ou agrandit l'image, proportions gardées, pour que son plus grand côté fasse
    IMAGE_OUTPUT_MAX_SIDE_PX : 4000 × 3000 donne 512 × 384, 200 × 100 donne 512 × 256.

    Lanczos est le filtre d'interpolation classique de meilleure qualité, dans les deux sens.
    Agrandir n'invente pas de détails : une toute petite image sort lisse, un peu floue.
    """
    scale: float = IMAGE_OUTPUT_MAX_SIDE_PX / max(image.width, image.height)
    target_size: tuple[int, int] = (
        max(1, round(image.width * scale)),
        max(1, round(image.height * scale)),
    )
    if target_size == image.size:
        return image
    # reducing_gap accélère les fortes réductions sans perte visible ; sans effet pour agrandir
    return image.resize(target_size, Image.Resampling.LANCZOS, reducing_gap=3.0)
