from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from cache import update_metadata_cache


def setup_scheduler() -> AsyncIOScheduler:
    """
    Set up apscheduler to regularly update the metadata cache.
    """
    scheduler = AsyncIOScheduler(timezone=UTC)
    hourly_trigger = IntervalTrigger(hours=1)
    now = datetime.now(tz=UTC)
    logger.info("Adding hourly job to update metadata cache...")
    scheduler.add_job(
        update_metadata_cache,
        trigger=hourly_trigger,
        next_run_time=now,
        id="update_metadata_cache",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    scheduler.start()
    return scheduler
