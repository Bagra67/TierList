import asyncio
import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

SweepHandler = Callable[[], Awaitable[None]]


class RoomSweeper:
    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None

    def start(self, interval_seconds: float, sweep: SweepHandler) -> None:
        """Appelé au démarrage du processus, dans la boucle asyncio : premier balayage après un
        intervalle, le temps que les participants connectés avant un redémarrage reviennent."""
        self._task = asyncio.create_task(self._run(interval_seconds, sweep))

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        await asyncio.gather(self._task, return_exceptions=True)
        self._task = None

    async def _run(self, interval_seconds: float, sweep: SweepHandler) -> None:
        while True:
            await asyncio.sleep(interval_seconds)
            try:
                await sweep()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Balayage des salles inactives en échec")


room_sweeper: RoomSweeper = RoomSweeper()
