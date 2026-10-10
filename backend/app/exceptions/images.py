class ImageUnsupportedFormatError(Exception):
    """Le fichier n'est pas une image d'un format accepté (JPEG, PNG, WebP), ou est illisible."""


class ImageTooLargeError(Exception):
    """Le fichier reçu dépasse IMAGE_UPLOAD_MAX_BYTES."""

    def __init__(self, max_bytes: int) -> None:
        super().__init__(max_bytes)
        self.max_bytes = max_bytes


class ImageTooManyPixelsError(Exception):
    """L'image décodée dépasserait IMAGE_MAX_SOURCE_PIXELS (protection contre les bombes de
    décompression : un petit fichier qui se décode en une image immense)."""
