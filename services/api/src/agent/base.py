"""Shared agent infrastructure: step timing and run lifecycle utilities."""

import time
from typing import Any, Callable, Coroutine, List, Optional

from models.entities.couchbase.agent_runs import ScoreBreakdown, TraceStep
from models.operations.agent_runs import (
    agent_run_append_step,
    agent_run_get_by_owner,
)
from utils import log

logger = log.get_logger(__name__)


async def timed_step(
    run_id: str,
    step_index: int,
    step_type: str,
    label: str,
    func: Callable[[], Coroutine[Any, Any, Any]],
    input_data: Any = None,
    listings_considered: Optional[List[str]] = None,
    score_breakdown: Optional[ScoreBreakdown] = None,
) -> Any:
    """Execute an async function, time it, and persist the result as a TraceStep."""
    start = time.monotonic()
    try:
        result = await func()
        duration_ms = int((time.monotonic() - start) * 1000)
        step = TraceStep(
            step_index=step_index,
            step_type=step_type,
            label=label,
            input=input_data,
            output=result if not isinstance(result, (list, dict)) or len(str(result)) < 5000 else f"[{type(result).__name__} len={len(result)}]",
            duration_ms=duration_ms,
            listings_considered=listings_considered or [],
            score_breakdown=score_breakdown,
        )
        await agent_run_append_step(run_id, step)
        return result
    except Exception as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        step = TraceStep(
            step_index=step_index,
            step_type=step_type,
            label=f"{label} (FAILED)",
            input=input_data,
            output={"error": str(e)},
            duration_ms=duration_ms,
            listings_considered=listings_considered or [],
        )
        await agent_run_append_step(run_id, step)
        raise


async def check_no_running_run(owner_id: str, agent_type: str) -> bool:
    """Return True if there is no currently running agent run for this owner/type."""
    runs = await agent_run_get_by_owner(owner_id, agent_type=agent_type, limit=5)
    for run in runs:
        if run.data.status == "running":
            logger.warning(
                f"Skipping {agent_type} for {owner_id}: run {run.id} already running"
            )
            return False
    return True
