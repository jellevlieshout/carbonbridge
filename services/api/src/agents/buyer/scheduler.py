"""
APScheduler setup for autonomous buyer agent runs.

Changed from nightly to hourly so that new listings picked up from
OffsetsDB sync or manually added by sellers are acted on quickly.
Idempotency is preserved by check_no_running_run in the agent itself.
"""

from typing import Optional
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from models.operations.users import user_get_agent_enabled_buyers
from utils import log

from .agent import run_buyer_agent

logger = log.get_logger(__name__)

_scheduler: Optional[AsyncIOScheduler] = None


async def hourly_buyer_job():
    """Run the autonomous buyer agent for all enabled buyers (every hour)."""
    logger.info("Hourly autonomous buyer agent job starting...")

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
                logger.info(f"Agent run {run_id} completed/started for buyer {buyer.id}")
            else:
                logger.debug(f"Agent run skipped for buyer {buyer.id} (already running)")
        except Exception as e:
            logger.error(f"Agent run failed for buyer {buyer.id}: {e}", exc_info=True)

    logger.info("Hourly autonomous buyer agent job completed")


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
    """Start the APScheduler with the hourly buyer agent job."""
    global _scheduler
    _scheduler = AsyncIOScheduler()

    # Hourly buyer agent check (every hour at :00)
    _scheduler.add_job(
        hourly_buyer_job,
        trigger=IntervalTrigger(hours=1),
        id="hourly_buyer_agent",
        name="Hourly Autonomous Buyer Agent",
        replace_existing=True,
        max_instances=1,  # prevent overlap
    )

    # Weekly OffsetsDB sync (Sunday 03:00 UTC)
    _scheduler.add_job(
        offsets_db_sync_job,
        trigger=CronTrigger(day_of_week="sun", hour=3, minute=0, timezone=ZoneInfo("UTC")),
        id="weekly_offsets_db_sync",
        name="Weekly OffsetsDB Sync",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        "APScheduler started: hourly buyer agent checks + weekly OffsetsDB sync (Sun 03:00 UTC)"
    )
    return _scheduler


def shutdown_scheduler():
    """Gracefully shut down the scheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("APScheduler shut down")
