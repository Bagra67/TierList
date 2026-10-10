from io import BytesIO

import pytest
from PIL import Image, ImageCms

from app.constants.images import IMAGE_OUTPUT_MAX_SIDE_PX
from app.exceptions.images import ImageTooManyPixelsError, ImageUnsupportedFormatError
from app.services.image_processing import CompressedImage, compress_image
from tests.image_files import make_image_file

# Assez grand pour les images des tests, comme la valeur par défaut de IMAGE_MAX_SOURCE_PIXELS
MAX_SOURCE_PIXELS: int = 40_000_000
# Balise EXIF Orientation : 6 = l'image doit être tournée de 90° dans le sens horaire
EXIF_ORIENTATION_TAG: int = 0x0112
EXIF_MAKE_TAG: int = 0x010F


def open_output(compressed: CompressedImage) -> Image.Image:
    return Image.open(BytesIO(compressed.data))


def pixel_channels(image: Image.Image, position: tuple[int, int]) -> tuple[int, ...]:
    """Valeurs des canaux d'un pixel d'une image en couleurs (RGB ou RGBA)."""
    channels: object = image.getpixel(position)
    assert isinstance(channels, tuple)
    return channels


@pytest.mark.parametrize("image_format", ["JPEG", "PNG", "WEBP"])
def test_accepted_formats_are_reencoded_in_webp(image_format: str) -> None:
    content: bytes = make_image_file((600, 400), image_format)

    compressed: CompressedImage = compress_image(content, MAX_SOURCE_PIXELS)

    output: Image.Image = open_output(compressed)
    assert output.format == "WEBP"
    assert output.size == (compressed.width, compressed.height)


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(make_image_file((40, 40), "GIF"), id="gif"),
        pytest.param(
            b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>', id="svg"
        ),
        pytest.param(b"just some text", id="text"),
        # Début d'un fichier HEIC (photo d'iPhone) : Pillow n'a pas de décodeur HEIC
        pytest.param(b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic", id="heic"),
        pytest.param(b"", id="empty"),
        # JPEG coupé en deux : l'en-tête est valide, les pixels manquent
        pytest.param(make_image_file((600, 400), "JPEG")[:300], id="truncated-jpeg"),
    ],
)
def test_other_files_are_refused(content: bytes) -> None:
    with pytest.raises(ImageUnsupportedFormatError):
        compress_image(content, MAX_SOURCE_PIXELS)


def test_too_many_pixels_are_refused_before_decoding() -> None:
    content: bytes = make_image_file((20, 20), "PNG")

    with pytest.raises(ImageTooManyPixelsError):
        compress_image(content, max_source_pixels=399)


def test_the_pixel_limit_is_inclusive() -> None:
    content: bytes = make_image_file((20, 20), "PNG")

    compressed: CompressedImage = compress_image(content, max_source_pixels=400)

    assert compressed.width == IMAGE_OUTPUT_MAX_SIDE_PX


@pytest.mark.parametrize(
    ("source_size", "expected_size"),
    [
        pytest.param((4000, 3000), (512, 384), id="large-landscape"),
        pytest.param((1000, 2000), (256, 512), id="large-portrait"),
        pytest.param((200, 100), (512, 256), id="small-landscape"),
        pytest.param((30, 60), (256, 512), id="small-portrait"),
        pytest.param((1, 1), (512, 512), id="single-pixel"),
        pytest.param((512, 300), (512, 300), id="already-512"),
    ],
)
def test_the_longest_side_is_resized_to_512_keeping_proportions(
    source_size: tuple[int, int], expected_size: tuple[int, int]
) -> None:
    content: bytes = make_image_file(source_size, "PNG")

    compressed: CompressedImage = compress_image(content, MAX_SOURCE_PIXELS)

    assert (compressed.width, compressed.height) == expected_size
    assert open_output(compressed).size == expected_size


def test_exif_orientation_is_applied() -> None:
    exif: Image.Exif = Image.Exif()
    exif[EXIF_ORIENTATION_TAG] = 6
    # Photo prise téléphone tourné : stockée en paysage, à afficher en portrait
    content: bytes = make_image_file((400, 200), "JPEG", exif=exif.tobytes())

    compressed: CompressedImage = compress_image(content, MAX_SOURCE_PIXELS)

    assert (compressed.width, compressed.height) == (256, 512)


def test_metadata_is_removed() -> None:
    exif: Image.Exif = Image.Exif()
    exif[EXIF_MAKE_TAG] = "PhoneMaker"
    content: bytes = make_image_file((400, 200), "JPEG", exif=exif.tobytes())

    compressed: CompressedImage = compress_image(content, MAX_SOURCE_PIXELS)

    output: Image.Image = open_output(compressed)
    assert len(output.getexif()) == 0
    assert "exif" not in output.info
    assert b"PhoneMaker" not in compressed.data


def test_the_color_profile_is_kept() -> None:
    srgb_profile: bytes = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    content: bytes = make_image_file((400, 200), "JPEG", icc_profile=srgb_profile)

    compressed: CompressedImage = compress_image(content, MAX_SOURCE_PIXELS)

    assert open_output(compressed).info.get("icc_profile") == srgb_profile


@pytest.mark.parametrize("image_format", ["PNG", "WEBP"])
def test_transparency_is_kept(image_format: str) -> None:
    content: bytes = make_image_file(
        (100, 100), image_format, mode="RGBA", color=(0, 0, 255, 0), lossless=True
    )

    compressed: CompressedImage = compress_image(content, MAX_SOURCE_PIXELS)

    output: Image.Image = open_output(compressed)
    assert output.mode == "RGBA"
    assert pixel_channels(output, (10, 10))[3] == 0


def test_an_opaque_image_has_no_alpha_channel() -> None:
    content: bytes = make_image_file((100, 100), "JPEG")

    compressed: CompressedImage = compress_image(content, MAX_SOURCE_PIXELS)

    assert open_output(compressed).mode == "RGB"


def test_only_the_first_frame_of_an_animated_image_is_kept() -> None:
    frames: list[Image.Image] = [
        Image.new("RGB", (100, 100), (255, 0, 0)),
        Image.new("RGB", (100, 100), (0, 255, 0)),
    ]
    buffer: BytesIO = BytesIO()
    frames[0].save(buffer, format="WEBP", save_all=True, append_images=frames[1:], lossless=True)

    compressed: CompressedImage = compress_image(buffer.getvalue(), MAX_SOURCE_PIXELS)

    output: Image.Image = open_output(compressed)
    assert getattr(output, "n_frames", 1) == 1
    red, green, _blue = pixel_channels(output.convert("RGB"), (50, 50))
    assert red > 200
    assert green < 50
