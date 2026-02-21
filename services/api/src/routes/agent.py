"""
API endpoints for agent runs (buyer + seller advisory).

POST /agent/trigger              — manually trigger buyer agent
POST /agent/trigger-advisory     — manually trigger seller advisory agent
GET  /agent/runs                 — list user's agent runs (optional ?agent_type filter)
GET  /agent/runs/{run_id}        — get run detail with trace steps
GET  /agent/runs/{run_id}/export — raw AgentRun document as JSON
POST /agent/runs/{id}/approve    — approve a proposed purchase
POST /agent/runs/{id}/reject     — reject a proposed purchase
"""

from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from agent.buyer_agent import run_buyer_agent
from agent.seller_agent import run_seller_advisory_agent
from models.entities.couchbase.orders import OrderLineItem
from models.entities.couchbase.users import User
from models.operations.agent_runs import (
    agent_run_complete,
    agent_run_get,
    agent_run_get_by_owner,
)
from models.operations.listings import listing_get, listing_reserve_quantity
from models.operations.orders import (
    order_create,
    order_set_payment_intent,
    order_update_status,
)
from utils import env, log

from .dependencies import require_authenticated, require_seller

logger = log.get_logger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class TriggerResponse(BaseModel):
    run_id: str
    status: str
    message: str


class AgentRunSummary(BaseModel):
    id: str
    agent_type: str
    status: str
    trigger_reason: str
    action_taken: Optional[str] = None
    triggered_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    final_selection_id: Optional[str] = None
    order_id: Optional[str] = None
    error_message: Optional[str] = None
    selection_rationale: Optional[str] = None


class AgentRunDetail(AgentRunSummary):
    trace_steps: List[Any] = []
    listings_shortlisted: List[str] = []


# ---------------------------------------------------------------------------
# POST /agent/trigger
# ---------------------------------------------------------------------------

@router.post("/trigger", response_model=TriggerResponse, status_code=202)
async def route_agent_trigger(
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_authenticated),
):
    """Manually trigger the autonomous buyer agent for the current user."""
    buyer_id = user["sub"]

    # Launch agent as background task so the response returns immediately
    background_tasks.add_task(run_buyer_agent, buyer_id, "manual")

    return TriggerResponse(
        run_id="pending",
        status="running",
        message="Agent run triggered. Poll GET /api/agent/runs for results.",
    )


# ---------------------------------------------------------------------------
# GET /agent/runs
# ---------------------------------------------------------------------------

@router.get("/runs", response_model=List[AgentRunSummary])
async def route_agent_runs(
    agent_type: Optional[str] = None,
    user: dict = Depends(require_authenticated),
):
    """List the authenticated user's agent runs, optionally filtered by agent_type."""
    owner_id = user["sub"]
    runs = await agent_run_get_by_owner(owner_id, agent_type=agent_type)
    return [
        AgentRunSummary(
            id=r.id,
            agent_type=r.data.agent_type,
            status=r.data.status,
            trigger_reason=r.data.trigger_reason,
            action_taken=r.data.action_taken,
            triggered_at=r.data.triggered_at,
            completed_at=r.data.completed_at,
            final_selection_id=r.data.final_selection_id,
            order_id=r.data.order_id,
            error_message=r.data.error_message,
            selection_rationale=r.data.selection_rationale,
        )
        for r in runs
    ]


# ---------------------------------------------------------------------------
# GET /agent/runs/{run_id}
# ---------------------------------------------------------------------------

@router.get("/runs/{run_id}", response_model=AgentRunDetail)
async def route_agent_run_detail(
    run_id: str, user: dict = Depends(require_authenticated)
):
    """Get a single agent run with full trace steps."""
    run = await agent_run_get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    if run.data.owner_id != user["sub"]:
        raise HTTPException(status_code=403, detail="Not your agent run")

    return AgentRunDetail(
        id=run.id,
        agent_type=run.data.agent_type,
        status=run.data.status,
        trigger_reason=run.data.trigger_reason,
        action_taken=run.data.action_taken,
        triggered_at=run.data.triggered_at,
        completed_at=run.data.completed_at,
        final_selection_id=run.data.final_selection_id,
        order_id=run.data.order_id,
        error_message=run.data.error_message,
        selection_rationale=run.data.selection_rationale,
        trace_steps=[s.model_dump() for s in run.data.trace_steps],
        listings_shortlisted=run.data.listings_shortlisted,
    )


# ---------------------------------------------------------------------------
# GET /agent/runs/{run_id}/export — raw AgentRun document as JSON
# ---------------------------------------------------------------------------

@router.get("/runs/{run_id}/export")
async def route_agent_run_export(
    run_id: str, user: dict = Depends(require_authenticated)
):
    """Export the full AgentRun document as JSON (spec section 5.8.4)."""
    run = await agent_run_get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    if run.data.owner_id != user["sub"]:
        raise HTTPException(status_code=403, detail="Not your agent run")

    return run.data.model_dump(mode="json")


# ---------------------------------------------------------------------------
# POST /agent/runs/{run_id}/approve
# ---------------------------------------------------------------------------

@router.post("/runs/{run_id}/approve", response_model=AgentRunDetail)
async def route_agent_run_approve(
    run_id: str, user: dict = Depends(require_authenticated)
):
    """Approve a proposed purchase from an awaiting_approval agent run."""
    run = await agent_run_get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    if run.data.owner_id != user["sub"]:
        raise HTTPException(status_code=403, detail="Not your agent run")
    if run.data.status != "awaiting_approval":
        raise HTTPException(
            status_code=400,
            detail=f"Run is not awaiting approval (status: {run.data.status})",
        )
    if not run.data.final_selection_id:
        raise HTTPException(status_code=400, detail="No listing selected for this run")

    buyer_id = user["sub"]
    listing = await listing_get(run.data.final_selection_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Selected listing no longer exists")

    # Determine quantity and price from the run's trace steps (use stored values)
    quantity = None
    price_per_tonne = None
    for step in run.data.trace_steps:
        if step.label == "Selected best match" and isinstance(step.output, dict):
            quantity = step.output.get("quantity_tonnes")
            price_per_tonne = step.output.get("price_per_tonne_eur")
            break

    if not quantity or quantity < 1:
        raise HTTPException(status_code=400, detail="Could not determine purchase quantity")

    # Use the price from when the agent made its decision, not the current listing price
    if not price_per_tonne:
        price_per_tonne = listing.data.price_per_tonne_eur

    total_cost = round(quantity * price_per_tonne, 2)

    # Reserve and create order
    reserved = await listing_reserve_quantity(listing.id, quantity)
    if not reserved:
        raise HTTPException(
            status_code=409,
            detail=f"Could not reserve {quantity}t on listing {listing.id}",
        )

    line_items = [
        OrderLineItem(
            listing_id=listing.id,
            quantity=quantity,
            price_per_tonne=price_per_tonne,
            subtotal=total_cost,
        )
    ]
    order = await order_create(buyer_id, line_items, total_cost)

    # Mock payment
    import hashlib
    mock_id = f"pi_agent_{hashlib.sha256(order.id.encode()).hexdigest()[:16]}"
    await order_set_payment_intent(order.id, mock_id)
    await order_update_status(order.id, "confirmed")

    # Complete the run
    await agent_run_complete(
        run_id,
        action_taken="purchased",
        order_id=order.id,
    )

    updated = await agent_run_get(run_id)
    return AgentRunDetail(
        id=updated.id,
        agent_type=updated.data.agent_type,
        status=updated.data.status,
        trigger_reason=updated.data.trigger_reason,
        action_taken=updated.data.action_taken,
        triggered_at=updated.data.triggered_at,
        completed_at=updated.data.completed_at,
        final_selection_id=updated.data.final_selection_id,
        order_id=updated.data.order_id,
        error_message=updated.data.error_message,
        selection_rationale=updated.data.selection_rationale,
        trace_steps=[s.model_dump() for s in updated.data.trace_steps],
        listings_shortlisted=updated.data.listings_shortlisted,
    )


# ---------------------------------------------------------------------------
# POST /agent/runs/{run_id}/reject
# ---------------------------------------------------------------------------

@router.post("/runs/{run_id}/reject", response_model=AgentRunDetail)
async def route_agent_run_reject(
    run_id: str, user: dict = Depends(require_authenticated)
):
    """Reject a proposed purchase."""
    run = await agent_run_get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    if run.data.owner_id != user["sub"]:
        raise HTTPException(status_code=403, detail="Not your agent run")
    if run.data.status != "awaiting_approval":
        raise HTTPException(
            status_code=400,
            detail=f"Run is not awaiting approval (status: {run.data.status})",
        )

    await agent_run_complete(run_id, action_taken="skipped",
        selection_rationale="Rejected by buyer")

    updated = await agent_run_get(run_id)
    return AgentRunDetail(
        id=updated.id,
        agent_type=updated.data.agent_type,
        status=updated.data.status,
        trigger_reason=updated.data.trigger_reason,
        action_taken=updated.data.action_taken,
        triggered_at=updated.data.triggered_at,
        completed_at=updated.data.completed_at,
        final_selection_id=updated.data.final_selection_id,
        order_id=updated.data.order_id,
        error_message=updated.data.error_message,
        selection_rationale=updated.data.selection_rationale,
        trace_steps=[s.model_dump() for s in updated.data.trace_steps],
        listings_shortlisted=updated.data.listings_shortlisted,
    )


# ---------------------------------------------------------------------------
# POST /agent/trigger-advisory
# ---------------------------------------------------------------------------

@router.post("/trigger-advisory", response_model=TriggerResponse, status_code=202)
async def route_agent_trigger_advisory(
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_seller),
):
    """Manually trigger the seller advisory agent for the current user (seller role required)."""
    seller_id = user["sub"]

    background_tasks.add_task(run_seller_advisory_agent, seller_id, "manual")

    return TriggerResponse(
        run_id="pending",
        status="running",
        message="Seller advisory agent triggered. Poll GET /api/agent/runs?agent_type=seller_advisory for results.",
    )
