from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger


class SchedulerService:
    def __init__(self, tz: str) -> None:
        self._scheduler = AsyncIOScheduler(timezone=tz)

    async def start(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()

    async def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    def add_job(self, job_id: str, run_at: datetime, func: Callable[..., Any], **kwargs: Any) -> None:
        trigger = DateTrigger(run_date=run_at)
        self._scheduler.add_job(func, trigger=trigger, id=job_id, replace_existing=True, kwargs=kwargs)

    def remove_job(self, job_id: str) -> None:
        try:
            self._scheduler.remove_job(job_id)
        except Exception:
            # job may be absent (already executed/removed)
            return

    def has_job(self, job_id: str) -> bool:
        return self._scheduler.get_job(job_id) is not None

