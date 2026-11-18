import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from app.exceptions.moderation import ImagesHidingInProgressError


class ImageHidingGuard:
    def __init__(self) -> None:
        self._lock: threading.Lock = threading.Lock()
        self._accounts_in_progress: set[uuid.UUID] = set()

    @contextmanager
    def hold(self, user_id: uuid.UUID) -> Iterator[None]:
        with self._lock:
            if user_id in self._accounts_in_progress:
                raise ImagesHidingInProgressError
            self._accounts_in_progress.add(user_id)
        try:
            yield
        finally:
            with self._lock:
                self._accounts_in_progress.discard(user_id)


image_hiding_guard: ImageHidingGuard = ImageHidingGuard()
