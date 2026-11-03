from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageOps

from app.constants.images import (
    ACCEPTED_IMAGE_FORMATS,
    IMAGE_FAST_DOWNSCALE_REDUCING_GAP,
    IMAGE_OUTPUT_MAX_SIDE_PX,
    IMAGE_WEBP_QUALITY,
)
from app.exceptions.images import ImageTooManyPixelsError, ImageUnsupportedFormatError

_INVALID_IMAGE_ERRORS: tuple[type[Exception], ...] = (OSError, SyntaxError, ValueError)


@dataclass(frozen=True)
class CompressedImage:
    data: bytes
    width: int
    height: int


def compress_image(content: bytes, max_source_pixels: int) -> CompressedImage:
    _verify(content, max_source_pixels)
    try:
        with Image.open(BytesIO(content), formats=ACCEPTED_IMAGE_FORMATS) as source:
            source.draft(None, (IMAGE_OUTPUT_MAX_SIDE_PX, IMAGE_OUTPUT_MAX_SIDE_PX))
            source.load()
            icc_profile: bytes | None = source.info.get("icc_profile")
            upright: Image.Image = ImageOps.exif_transpose(source)
            converted: Image.Image = _convert_mode(upright)
    except Image.DecompressionBombError as exc:
        raise ImageTooManyPixelsError from exc
    except _INVALID_IMAGE_ERRORS as exc:
        raise ImageUnsupportedFormatError from exc

    resized: Image.Image = _fit_to_output_size(converted)
    output: BytesIO = BytesIO()
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
    if image.has_transparency_data:
        return image.convert("RGBA")
    return image.convert("RGB")


def _fit_to_output_size(image: Image.Image) -> Image.Image:
    scale: float = IMAGE_OUTPUT_MAX_SIDE_PX / max(image.width, image.height)
    target_size: tuple[int, int] = (
        max(1, round(image.width * scale)),
        max(1, round(image.height * scale)),
    )
    if target_size == image.size:
        return image
    return image.resize(
        target_size, Image.Resampling.LANCZOS, reducing_gap=IMAGE_FAST_DOWNSCALE_REDUCING_GAP
    )
