"""APScheduler setup for nightly autonomous buyer agent runs."""

from typing import Optional
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from models.operations.users import user_get_agent_enabled_buyers
from utils import log

from .buyer_agent import run_buyer_agent

logger = log.get_logger(__name__)

_scheduler: Optional[AsyncIOScheduler] = None


async def nightly_buyer_job():
    """Run the autonomous buyer agent for all enabled buyers."""
    logger.info("Nightly autonomous buyer agent job starting...")

    try:
        buyers = await user_get_agent_enabled_buyers()
    except Exception as e:
        logger.error(f"Failed to query agent-enabled buyers: {e}")
        return

    logger.info(f"Found {len(buyers)} buyers with autonomous agent enabled")

    for buyer in buyers:
        try:
            run_id = await run_buyer_agent(buyer.id, trigger="scheduled")
            if run_id:
                logger.info(f"Agent run {run_id} completed for buyer {buyer.id}")
            else:
                logger.info(f"Agent run skipped for buyer {buyer.id} (already running)")
        except Exception as e:
            logger.error(f"Agent run failed for buyer {buyer.id}: {e}", exc_info=True)

    logger.info("Nightly autonomous buyer agent job completed")


async def offsets_db_sync_job():
    """Weekly sync of OffsetsDB data from CarbonPlan."""
    logger.info("Weekly OffsetsDB sync job starting...")
    try:
        from offsets_db_sync import run_offsets_db_sync

        result = await run_offsets_db_sync()
        logger.info(f"OffsetsDB sync job finished: {result.get('status')}")
    except Exception as e:
        logger.error(f"OffsetsDB sync job failed: {e}", exc_info=True)


def init_scheduler() -> AsyncIOScheduler:
    """Start the APScheduler with the nightly buyer agent job."""
    global _scheduler
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        nightly_buyer_job,
        trigger=CronTrigger(hour=2, minute=0, timezone=ZoneInfo("UTC")),
        id="nightly_buyer_agent",
        name="Nightly Autonomous Buyer Agent",
        replace_existing=True,
    )
    _scheduler.add_job(
        offsets_db_sync_job,
        trigger=CronTrigger(day_of_week="sun", hour=3, minute=0, timezone=ZoneInfo("UTC")),
        id="weekly_offsets_db_sync",
        name="Weekly OffsetsDB Sync",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("APScheduler started with nightly buyer agent (02:00 UTC) and weekly OffsetsDB sync (Sun 03:00 UTC)")
    return _scheduler


def shutdown_scheduler():
    """Gracefully shut down the scheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("APScheduler shut down")
