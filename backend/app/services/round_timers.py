"""Timers des parties, côté serveur (docs/technical/realtime.md, §2.8).

Étape 0 : un seul worker, une tâche asyncio par partie qui attend sa prochaine échéance (la fin
du timer de son tour en cours, ou la fin du cooldown final), puis appelle la transition du
service. Les transitions sont idempotentes (elles vérifient, sous le verrou de la salle, que le
tour ou le cooldown attendu est toujours en cours) : une phase finie plus tôt (« suivant », « tout
le monde a placé », « Terminer maintenant ») ne demande donc pas d'annuler sa tâche.
"""

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from functools import partial
from typing import Protocol

logger = logging.getLogger(__name__)

# Termine le tour round_number de la partie game_id ; sans effet s'il n'est plus en cours
DeadlineHandler = Callable[[uuid.UUID, int], Awaitable[None]]
# Termine le cooldown final de la partie game_id ; sans effet s'il n'est plus en cours
CooldownDeadlineHandler = Callable[[uuid.UUID], Awaitable[None]]


class RoundScheduler(Protocol):
    def schedule(self, game_id: uuid.UUID, round_number: int, ends_at: datetime) -> None:
        """Termine ce tour à ends_at. Appelé après le commit, depuis n'importe quel thread."""
        ...

    def schedule_cooldown_end(self, game_id: uuid.UUID, ends_at: datetime) -> None:
        """Termine le cooldown final de cette partie à ends_at, comme schedule."""
        ...


class RoundTimers:
    """Une échéance au plus par partie : celle de son tour en cours, ou celle de son cooldown.

    Les tâches ne vivent que dans la boucle asyncio ; schedule peut être appelé depuis le
    threadpool (routes REST synchrones) : la création de la tâche est alors confiée à la boucle.
    """

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._on_deadline: DeadlineHandler | None = None
        self._on_cooldown_deadline: CooldownDeadlineHandler | None = None
        self._tasks: dict[uuid.UUID, asyncio.Task[None]] = {}

    def start(
        self,
        loop: asyncio.AbstractEventLoop,
        on_deadline: DeadlineHandler,
        on_cooldown_deadline: CooldownDeadlineHandler,
    ) -> None:
        """Appelé au démarrage du processus, avant de reprogrammer les échéances en attente."""
        self._loop = loop
        self._on_deadline = on_deadline
        self._on_cooldown_deadline = on_cooldown_deadline

    async def stop(self) -> None:
        """Annule les échéances à l'arrêt du processus : elles seront reprogrammées depuis la base
        au prochain démarrage."""
        tasks: list[asyncio.Task[None]] = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()
        self._loop = None
        self._on_deadline = None
        self._on_cooldown_deadline = None

    def schedule(self, game_id: uuid.UUID, round_number: int, ends_at: datetime) -> None:
        self._schedule(
            game_id,
            ends_at,
            partial(self._end_round, game_id, round_number),
            f"round={round_number}",
        )

    def schedule_cooldown_end(self, game_id: uuid.UUID, ends_at: datetime) -> None:
        self._schedule(game_id, ends_at, partial(self._end_cooldown, game_id), "cooldown")

    async def _end_round(self, game_id: uuid.UUID, round_number: int) -> None:
        if self._on_deadline is not None:
            await self._on_deadline(game_id, round_number)

    async def _end_cooldown(self, game_id: uuid.UUID) -> None:
        if self._on_cooldown_deadline is not None:
            await self._on_cooldown_deadline(game_id)

    def _schedule(
        self,
        game_id: uuid.UUID,
        ends_at: datetime,
        transition: Callable[[], Awaitable[None]],
        phase: str,
    ) -> None:
        if self._loop is None or self._loop.is_closed():
            # Pas démarré (tests sans lifespan) : l'échéance sera relue en base au démarrage
            return
        self._loop.call_soon_threadsafe(self._replace, game_id, ends_at, transition, phase)

    def _replace(
        self,
        game_id: uuid.UUID,
        ends_at: datetime,
        transition: Callable[[], Awaitable[None]],
        phase: str,
    ) -> None:
        # La phase précédente de la partie est finie : son échéance n'a plus d'objet
        previous: asyncio.Task[None] | None = self._tasks.pop(game_id, None)
        if previous is not None:
            previous.cancel()
        self._tasks[game_id] = asyncio.create_task(
            self._end_at(game_id, ends_at, transition, phase)
        )

    async def _end_at(
        self,
        game_id: uuid.UUID,
        ends_at: datetime,
        transition: Callable[[], Awaitable[None]],
        phase: str,
    ) -> None:
        try:
            delay_seconds: float = (ends_at - datetime.now(UTC)).total_seconds()
            # Une échéance déjà passée (redémarrage pendant une phase) se déclenche tout de suite
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)
            await transition()
        except asyncio.CancelledError:
            raise
        except Exception:
            # Une tâche asyncio perdrait l'erreur en silence : elle est journalisée ici
            logger.exception("Échéance au timer en échec : game_id=%s %s", game_id, phase)
        finally:
            # Une tâche annulée puis remplacée ne doit pas retirer sa remplaçante
            if self._tasks.get(game_id) is asyncio.current_task():
                self._tasks.pop(game_id, None)


# Les timers de ce processus : l'état global assumé de l'étape 0 (un seul worker)
round_timers: RoundTimers = RoundTimers()
