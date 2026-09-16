"""
Thin interface over APScheduler so the underlying scheduler can be swapped
for Celery/Redis Queue/etc later without touching payment_scheduler.py's
job logic (docs/architecture.md §17 / §5 tech stack notes).
"""

from collections.abc import Callable

from apscheduler.schedulers.background import BackgroundScheduler


class SchedulerService:
    JOB_ID = "process_due_mandates"

    def __init__(self, job_fn: Callable[[], int], interval_seconds: int = 60) -> None:
        self._scheduler = BackgroundScheduler()
        self._job_fn = job_fn
        self._interval_seconds = interval_seconds

    def start(self) -> None:
        self._scheduler.add_job(
            self._job_fn,
            trigger="interval",
            seconds=self._interval_seconds,
            id=self.JOB_ID,
            replace_existing=True,
            max_instances=1,  # never let two ticks overlap on a slow run
        )
        self._scheduler.start()

    def stop(self) -> None:
        self._scheduler.shutdown(wait=False)


_scheduler_instance: SchedulerService | None = None


def get_scheduler_service() -> SchedulerService | None:
    return _scheduler_instance


def start_scheduler(job_fn: Callable[[], int], interval_seconds: int) -> None:
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = SchedulerService(job_fn, interval_seconds)
        _scheduler_instance.start()


def stop_scheduler() -> None:
    global _scheduler_instance
    if _scheduler_instance is not None:
        _scheduler_instance.stop()
        _scheduler_instance = None