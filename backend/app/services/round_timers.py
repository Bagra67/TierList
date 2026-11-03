import asyncio
import logging
import math
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from functools import partial
from typing import Protocol

from app.constants.games import TIMER_RETRY_DELAYS_SECONDS

logger = logging.getLogger(__name__)

# Termine le tour round_number de la partie game_id ; sans effet s'il n'est plus en cours
DeadlineHandler = Callable[[uuid.UUID, int], Awaitable[None]]
# Termine le cooldown final de la partie game_id ; sans effet s'il n'est plus en cours
CooldownDeadlineHandler = Callable[[uuid.UUID], Awaitable[None]]

COOLDOWN_RANK: float = math.inf


class RoundScheduler(Protocol):
    def schedule(self, game_id: uuid.UUID, round_number: int, ends_at: datetime) -> None: ...

    def schedule_cooldown_end(self, game_id: uuid.UUID, ends_at: datetime) -> None: ...


class RoundTimers:
    def __init__(
        self, retry_delays_seconds: tuple[float, ...] = TIMER_RETRY_DELAYS_SECONDS
    ) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._on_deadline: DeadlineHandler | None = None
        self._on_cooldown_deadline: CooldownDeadlineHandler | None = None
        self._retry_delays_seconds: tuple[float, ...] = retry_delays_seconds
        self._tasks: dict[uuid.UUID, asyncio.Task[None]] = {}
        self._ranks: dict[uuid.UUID, float] = {}

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
        tasks: list[asyncio.Task[None]] = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()
        self._ranks.clear()
        self._loop = None
        self._on_deadline = None
        self._on_cooldown_deadline = None

    def schedule(self, game_id: uuid.UUID, round_number: int, ends_at: datetime) -> None:
        self._schedule(
            game_id,
            ends_at,
            partial(self._end_round, game_id, round_number),
            round_number,
            f"round={round_number}",
        )

    def schedule_cooldown_end(self, game_id: uuid.UUID, ends_at: datetime) -> None:
        self._schedule(
            game_id, ends_at, partial(self._end_cooldown, game_id), COOLDOWN_RANK, "cooldown"
        )

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
        rank: float,
        phase: str,
    ) -> None:
        if self._loop is None or self._loop.is_closed():
            return
        self._loop.call_soon_threadsafe(self._replace, game_id, ends_at, transition, rank, phase)

    def _replace(
        self,
        game_id: uuid.UUID,
        ends_at: datetime,
        transition: Callable[[], Awaitable[None]],
        rank: float,
        phase: str,
    ) -> None:
        previous: asyncio.Task[None] | None = self._tasks.get(game_id)
        if previous is not None and rank < self._ranks.get(game_id, -math.inf):
            logger.info("Échéance dépassée ignorée : game_id=%s %s", game_id, phase)
            return
        if previous is not None:
            previous.cancel()
        self._ranks[game_id] = rank
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
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)
            await self._run_with_retries(game_id, transition, phase)
        finally:
            # Une tâche annulée puis remplacée ne doit pas retirer sa remplaçante
            if self._tasks.get(game_id) is asyncio.current_task():
                self._tasks.pop(game_id, None)
                self._ranks.pop(game_id, None)

    async def _run_with_retries(
        self, game_id: uuid.UUID, transition: Callable[[], Awaitable[None]], phase: str
    ) -> None:
        delays: tuple[float, ...] = (0.0, *self._retry_delays_seconds)
        for attempt, delay_seconds in enumerate(delays, start=1):
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)
            try:
                await transition()
                return
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "Échéance au timer en échec : game_id=%s %s essai=%d/%d",
                    game_id,
                    phase,
                    attempt,
                    len(delays),
                )


round_timers: RoundTimers = RoundTimers()
