import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

NightlyJob = Callable[[], Awaitable[int]]


def seconds_until_next_run(hour_utc: int, now: datetime) -> float:
    next_run: datetime = now.astimezone(UTC).replace(
        hour=hour_utc, minute=0, second=0, microsecond=0
    )
    if next_run <= now:
        next_run += timedelta(days=1)
    return (next_run - now).total_seconds()


class NightlyScheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None

    @property
    def is_running(self) -> bool:
        return self._task is not None

    def start(self, hour_utc: int, jobs: Mapping[str, NightlyJob]) -> None:
        self._task = asyncio.create_task(self._run(hour_utc, dict(jobs)))

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        await asyncio.gather(self._task, return_exceptions=True)
        self._task = None

    async def _run(self, hour_utc: int, jobs: dict[str, NightlyJob]) -> None:
        while True:
            await asyncio.sleep(seconds_until_next_run(hour_utc, datetime.now(UTC)))
            await run_nightly_jobs(jobs)


async def run_nightly_jobs(jobs: Mapping[str, NightlyJob]) -> None:
    for name, job in jobs.items():
        try:
            processed_count: int = await job()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Tâche de nuit en échec : %s", name)
            continue
        logger.info("Tâche de nuit terminée : %s, %d éléments", name, processed_count)


nightly_scheduler: NightlyScheduler = NightlyScheduler()
