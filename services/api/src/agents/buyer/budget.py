"""Monthly budget tracking for the autonomous buyer agent."""

from datetime import datetime, timezone

from models.operations.agent_runs import agent_run_get_by_owner
from models.operations.orders import order_get
from utils import log

logger = log.get_logger(__name__)


async def get_monthly_spend_eur(buyer_id: str) -> float:
    """Sum total_eur from orders created by agent runs this calendar month."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    runs = await agent_run_get_by_owner(buyer_id, agent_type="autonomous_buyer", limit=100)

    total_spend = 0.0
    for run in runs:
        # Only count completed purchases from this month
        if run.data.action_taken != "purchased":
            continue
        completed_at = run.data.completed_at
        if not completed_at:
            continue
        # Normalize to UTC if naive datetime (from Couchbase deserialization)
        if completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=timezone.utc)
        if completed_at < month_start:
            continue
        if run.data.order_id:
            order = await order_get(run.data.order_id)
            if order:
                total_spend += order.data.total_eur

    return round(total_spend, 2)


async def get_remaining_budget_eur(buyer_id: str, monthly_budget_eur: float) -> float:
    """Return how much budget remains for this month."""
    spent = await get_monthly_spend_eur(buyer_id)
    remaining = monthly_budget_eur - spent
    logger.info(
        f"Budget for {buyer_id}: spent={spent:.2f}, budget={monthly_budget_eur:.2f}, remaining={remaining:.2f}"
    )
    return round(remaining, 2)
