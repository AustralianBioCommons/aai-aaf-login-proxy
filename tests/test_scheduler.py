from datetime import UTC

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from cache.scheduler import setup_scheduler


@pytest.mark.asyncio
async def test_setup_scheduler_adds_hourly_job_and_starts_scheduler(mocker):
    async def fake_update_metadata_cache():
        pass

    mocker.patch(
        "cache.scheduler.update_metadata_cache",
        fake_update_metadata_cache,
    )

    scheduler = setup_scheduler()
    try:
        assert isinstance(scheduler, AsyncIOScheduler)
        assert scheduler.running is True
        assert scheduler.timezone == UTC

        job = scheduler.get_job("update_metadata_cache")
        assert job is not None
        assert job.func is fake_update_metadata_cache
        assert isinstance(job.trigger, IntervalTrigger)
        assert job.trigger.interval.total_seconds() == 60 * 60
    finally:
        scheduler.shutdown(wait=False)
