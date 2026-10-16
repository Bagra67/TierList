class ImageUnsupportedFormatError(Exception):
    """Le fichier n'est pas une image d'un format accepté (JPEG, PNG, WebP), ou est illisible."""


class ImageTooLargeError(Exception):
    """Le fichier reçu dépasse IMAGE_UPLOAD_MAX_BYTES."""

    def __init__(self, max_bytes: int) -> None:
        super().__init__(max_bytes)
        self.max_bytes = max_bytes


class ImageUploadLimitReachedError(Exception):
    """Le compte a déjà envoyé IMAGE_UPLOADS_PER_HOUR_MAX images dans l'heure écoulée."""

    def __init__(self, max_uploads: int) -> None:
        super().__init__(max_uploads)
        self.max_uploads = max_uploads


class ImageNotFoundError(Exception):
    """Image inexistante, ou appartenant à un autre utilisateur : les deux cas sont
    indiscernables, comme pour les templates."""


class ImageTooManyPixelsError(Exception):
    """L'image décodée dépasserait IMAGE_MAX_SOURCE_PIXELS (protection contre les bombes de
    décompression : un petit fichier qui se décode en une image immense)."""
