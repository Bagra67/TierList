"""Balayage périodique des salles inactives, côté serveur (docs/technical/realtime.md, §2.8).

Étape 0 : un seul worker, une tâche asyncio qui lance le balayage à intervalle régulier. Le
balayage ferme les salles inactives comme leur room admin (US-2.8) : il doit tourner dans le
processus qui tient les sockets, pour les fermer.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

# Ferme les salles inactives
SweepHandler = Callable[[], Awaitable[None]]


class RoomSweeper:
    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None

    def start(self, interval_seconds: float, sweep: SweepHandler) -> None:
        """Appelé au démarrage du processus, dans la boucle asyncio : premier balayage après un
        intervalle, le temps que les participants connectés avant un redémarrage reviennent."""
        self._task = asyncio.create_task(self._run(interval_seconds, sweep))

    async def stop(self) -> None:
        """Arrête le balayage à l'arrêt du processus."""
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
                # Une tâche asyncio perdrait l'erreur en silence, et s'arrêterait : l'erreur est
                # journalisée et le balayage suivant retentera (base injoignable un instant)
                logger.exception("Balayage des salles inactives en échec")


# Le balayage de ce processus : l'état global assumé de l'étape 0 (un seul worker)
room_sweeper: RoomSweeper = RoomSweeper()
