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
    """Transitions factices : gardent les tours terminés au timer, (partie, numéro du tour), et
    les cooldowns terminés, (partie)."""

    def __init__(self) -> None:
        self.ended: list[tuple[uuid.UUID, int]] = []
        self.cooldowns_ended: list[uuid.UUID] = []

    async def __call__(self, game_id: uuid.UUID, round_number: int) -> None:
        self.ended.append((game_id, round_number))

    async def end_cooldown(self, game_id: uuid.UUID) -> None:
        self.cooldowns_ended.append(game_id)


def test_a_deadline_ends_its_round():
    async def scenario() -> None:
        deadlines: RecordingDeadlines = RecordingDeadlines()
        timers: RoundTimers = RoundTimers()
        timers.start(asyncio.get_running_loop(), deadlines, deadlines.end_cooldown)

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
        timers.start(asyncio.get_running_loop(), deadlines, deadlines.end_cooldown)

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
        timers.start(asyncio.get_running_loop(), deadlines, deadlines.end_cooldown)

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
        timers.start(asyncio.get_running_loop(), deadlines, deadlines.end_cooldown)

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
        timers.start(asyncio.get_running_loop(), deadlines, deadlines.end_cooldown)
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

        async def no_cooldown(game_id: uuid.UUID) -> None:
            raise AssertionError("no cooldown in this test")

        timers: RoundTimers = RoundTimers()
        timers.start(asyncio.get_running_loop(), failing_for_game, no_cooldown)

        timers.schedule(GAME, 1, in_seconds(0))
        timers.schedule(OTHER_GAME, 1, in_seconds(0.02))
        await asyncio.sleep(0.1)

        # L'erreur est journalisée, l'autre partie avance quand même
        assert ended == [OTHER_GAME]
        await timers.stop()

    run(scenario)


def test_the_cooldown_end_replaces_the_deadline_of_the_last_round():
    async def scenario() -> None:
        deadlines: RecordingDeadlines = RecordingDeadlines()
        timers: RoundTimers = RoundTimers()
        timers.start(asyncio.get_running_loop(), deadlines, deadlines.end_cooldown)

        # "Suivant" sur le dernier tour avant son timer : le cooldown commence
        timers.schedule(GAME, 3, in_seconds(0.05))
        timers.schedule_cooldown_end(GAME, in_seconds(0.08))
        await asyncio.sleep(0.15)

        assert deadlines.ended == []
        assert deadlines.cooldowns_ended == [GAME]
        await timers.stop()

    run(scenario)


def test_an_older_deadline_never_replaces_a_newer_one():
    async def scenario() -> None:
        deadlines: RecordingDeadlines = RecordingDeadlines()
        timers: RoundTimers = RoundTimers()
        timers.start(asyncio.get_running_loop(), deadlines, deadlines.end_cooldown)

        # Le timer du tour 1 et « suivant » se croisent : le tour 3 est programmé avant le 2
        timers.schedule(GAME, 3, in_seconds(0.05))
        timers.schedule(GAME, 2, in_seconds(0.02))
        timers.schedule_cooldown_end(OTHER_GAME, in_seconds(0.02))
        timers.schedule(OTHER_GAME, 3, in_seconds(0.02))
        await asyncio.sleep(0.12)

        assert deadlines.ended == [(GAME, 3)]
        assert deadlines.cooldowns_ended == [OTHER_GAME]
        await timers.stop()

    run(scenario)


def test_a_failing_transition_is_tried_again():
    async def scenario() -> None:
        attempts: list[int] = []

        async def failing_once(game_id: uuid.UUID, round_number: int) -> None:
            attempts.append(round_number)
            if len(attempts) == 1:
                raise RuntimeError("database unreachable")

        async def no_cooldown(game_id: uuid.UUID) -> None:
            raise AssertionError("no cooldown in this test")

        timers: RoundTimers = RoundTimers(retry_delays_seconds=(0.02, 0.02))
        timers.start(asyncio.get_running_loop(), failing_once, no_cooldown)

        timers.schedule(GAME, 1, in_seconds(0))
        await asyncio.sleep(0.1)

        # Un premier échec, puis la transition réussit au deuxième essai, et s'arrête là
        assert attempts == [1, 1]
        await timers.stop()

    run(scenario)
