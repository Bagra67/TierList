class ImageUnsupportedFormatError(Exception):
    pass


class ImageTooLargeError(Exception):
    def __init__(self, max_bytes: int) -> None:
        super().__init__(max_bytes)
        self.max_bytes = max_bytes


class ImageUploadLimitReachedError(Exception):
    def __init__(self, max_uploads: int) -> None:
        super().__init__(max_uploads)
        self.max_uploads = max_uploads


class ImageNotFoundError(Exception):
    pass


class ImageTooManyPixelsError(Exception):
    pass


class ImageModerationConflictError(Exception):
    pass
