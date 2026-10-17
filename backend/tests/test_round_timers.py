import asyncio
import threading
import uuid
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime, timedelta
from typing import Any

from app.services.round_timers import RoundTimers

GAME: uuid.UUID = uuid.uuid4()
OTHER_GAME: uuid.UUID = uuid.uuid4()


def run(scenario: Callable[[], Coroutine[Any, Any, None]]) -> None:
    asyncio.run(scenario())


def in_seconds(seconds: float) -> datetime:
    return datetime.now(UTC) + timedelta(seconds=seconds)


class RecordingDeadlines:
    """Transition factice : garde les tours terminés au timer, (partie, numéro du tour)."""

    def __init__(self) -> None:
        self.ended: list[tuple[uuid.UUID, int]] = []

    async def __call__(self, game_id: uuid.UUID, round_number: int) -> None:
        self.ended.append((game_id, round_number))


def test_a_deadline_ends_its_round():
    async def scenario() -> None:
        deadlines: RecordingDeadlines = RecordingDeadlines()
        timers: RoundTimers = RoundTimers()
        timers.start(asyncio.get_running_loop(), deadlines)

        timers.schedule(GAME, 1, in_seconds(0.05))
        await asyncio.sleep(0.01)
        assert deadlines.ended == []
        await asyncio.sleep(0.1)

        assert deadlines.ended == [(GAME, 1)]
        await timers.stop()

    run(scenario)


def test_a_new_round_replaces_the_deadline_of_the_game():
    async def scenario() -> None:
        deadlines: RecordingDeadlines = RecordingDeadlines()
        timers: RoundTimers = RoundTimers()
        timers.start(asyncio.get_running_loop(), deadlines)

        timers.schedule(GAME, 1, in_seconds(0.05))
        timers.schedule(GAME, 2, in_seconds(0.08))
        timers.schedule(OTHER_GAME, 1, in_seconds(0.05))
        await asyncio.sleep(0.15)

        # Le tour 1 de GAME est fini avant son timer : seule l'échéance du tour 2 compte
        assert sorted(deadlines.ended) == sorted([(GAME, 2), (OTHER_GAME, 1)])
        await timers.stop()

    run(scenario)


def test_a_deadline_already_passed_fires_at_once():
    async def scenario() -> None:
        deadlines: RecordingDeadlines = RecordingDeadlines()
        timers: RoundTimers = RoundTimers()
        timers.start(asyncio.get_running_loop(), deadlines)

        # Le serveur était arrêté quand le timer a expiré
        timers.schedule(GAME, 3, in_seconds(-10))
        await asyncio.sleep(0.01)

        assert deadlines.ended == [(GAME, 3)]
        await timers.stop()

    run(scenario)


def test_a_deadline_can_be_scheduled_from_another_thread():
    async def scenario() -> None:
        deadlines: RecordingDeadlines = RecordingDeadlines()
        timers: RoundTimers = RoundTimers()
        timers.start(asyncio.get_running_loop(), deadlines)

        # Une route REST synchrone tourne dans le threadpool
        thread: threading.Thread = threading.Thread(
            target=timers.schedule, args=(GAME, 1, in_seconds(0.02))
        )
        thread.start()
        thread.join()
        await asyncio.sleep(0.1)

        assert deadlines.ended == [(GAME, 1)]
        await timers.stop()

    run(scenario)


def test_stopping_cancels_the_pending_deadlines():
    async def scenario() -> None:
        deadlines: RecordingDeadlines = RecordingDeadlines()
        timers: RoundTimers = RoundTimers()
        timers.start(asyncio.get_running_loop(), deadlines)
        timers.schedule(GAME, 1, in_seconds(0.05))
        await asyncio.sleep(0.01)

        await timers.stop()
        await asyncio.sleep(0.1)

        assert deadlines.ended == []
        # Arrêtés, les timers n'acceptent plus d'échéance : elles seront relues au démarrage
        timers.schedule(GAME, 2, in_seconds(0))
        await asyncio.sleep(0.01)
        assert deadlines.ended == []

    run(scenario)


def test_a_failing_transition_does_not_stop_the_other_deadlines():
    async def scenario() -> None:
        ended: list[uuid.UUID] = []

        async def failing_for_game(game_id: uuid.UUID, round_number: int) -> None:
            if game_id == GAME:
                raise RuntimeError("database unreachable")
            ended.append(game_id)

        timers: RoundTimers = RoundTimers()
        timers.start(asyncio.get_running_loop(), failing_for_game)

        timers.schedule(GAME, 1, in_seconds(0))
        timers.schedule(OTHER_GAME, 1, in_seconds(0.02))
        await asyncio.sleep(0.1)

        # L'erreur est journalisée, l'autre partie avance quand même
        assert ended == [OTHER_GAME]
        await timers.stop()

    run(scenario)
