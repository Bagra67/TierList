import asyncio

import pytest

from app.services.room_sweeper import RoomSweeper


def test_the_sweep_runs_at_each_interval():
    async def scenario() -> int:
        sweeper: RoomSweeper = RoomSweeper()
        sweeps: list[int] = []

        async def sweep() -> None:
            sweeps.append(len(sweeps))

        sweeper.start(0.01, sweep)
        await asyncio.sleep(0.1)
        await sweeper.stop()
        return len(sweeps)

    assert asyncio.run(scenario()) >= 2


def test_a_failed_sweep_is_logged_and_the_next_one_still_runs(caplog: pytest.LogCaptureFixture):
    async def scenario() -> int:
        sweeper: RoomSweeper = RoomSweeper()
        attempts: list[int] = []

        async def sweep() -> None:
            attempts.append(len(attempts))
            if len(attempts) == 1:
                raise RuntimeError("database unreachable")

        sweeper.start(0.01, sweep)
        await asyncio.sleep(0.1)
        await sweeper.stop()
        return len(attempts)

    assert asyncio.run(scenario()) >= 2
    assert "Balayage des salles inactives en échec" in caplog.text


def test_stopping_cancels_the_sweep():
    async def scenario() -> list[int]:
        sweeper: RoomSweeper = RoomSweeper()
        sweeps: list[int] = []

        async def sweep() -> None:
            sweeps.append(1)

        sweeper.start(0.05, sweep)
        await sweeper.stop()
        await asyncio.sleep(0.1)
        return sweeps

    # Arrêté avant son premier intervalle : aucun balayage
    assert asyncio.run(scenario()) == []
