import asyncio
from datetime import UTC, datetime

import pytest

from app.services.nightly_scheduler import (
    NightlyScheduler,
    run_nightly_jobs,
    seconds_until_next_run,
)


@pytest.mark.parametrize(
    ("now", "expected_seconds"),
    [
        # Avant l'heure : le jour même
        (datetime(2026, 10, 17, 1, 30, tzinfo=UTC), 90 * 60),
        # Après l'heure : le lendemain
        (datetime(2026, 10, 17, 4, 0, tzinfo=UTC), 23 * 3600),
        # Pile à l'heure (une exécution vient de commencer) : le lendemain, pas une seconde fois
        (datetime(2026, 10, 17, 3, 0, tzinfo=UTC), 24 * 3600),
        # Fin de mois : le passage au lendemain change de mois
        (datetime(2026, 10, 31, 23, 0, tzinfo=UTC), 4 * 3600),
    ],
)
def test_the_next_run_is_the_next_time_the_hour_comes(now: datetime, expected_seconds: int):
    assert seconds_until_next_run(3, now) == expected_seconds


def test_a_failing_job_is_logged_and_the_next_jobs_still_run(caplog: pytest.LogCaptureFixture):
    ran: list[str] = []

    async def failing() -> int:
        ran.append("failing")
        raise RuntimeError("storage unreachable")

    async def working() -> int:
        ran.append("working")
        return 2

    caplog.set_level("INFO")
    asyncio.run(run_nightly_jobs({"failing": failing, "working": working}))

    assert ran == ["failing", "working"]
    assert "Tâche de nuit en échec : failing" in caplog.text
    assert "Tâche de nuit terminée : working, 2 éléments" in caplog.text


def test_stopping_cancels_the_scheduler():
    async def scenario() -> tuple[bool, bool, list[int]]:
        scheduler: NightlyScheduler = NightlyScheduler()
        runs: list[int] = []

        async def job() -> int:
            runs.append(1)
            return 0

        scheduler.start(3, {"job": job})
        started: bool = scheduler.is_running
        await scheduler.stop()
        return started, scheduler.is_running, runs

    # Arrêté bien avant l'heure prévue : aucune exécution
    assert asyncio.run(scenario()) == (True, False, [])
