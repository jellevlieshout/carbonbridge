"""
Autonomous buyer agent orchestration (Pydantic AI + Gemini).

A Pydantic AI agent invoked by the nightly scheduler as a plain async
function — no streaming.  Runs to completion and returns a result object
written to an AgentRun document in Couchbase.  (Spec section 6.3)

Gemini 3 Flash drives the search → score → select decision flow through
structured tool calls.  Deterministic pre-checks (budget, idempotency)
and post-actions (order creation, payment) wrap the LLM step to keep
side-effects predictable.
"""

import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

try:
    from stripe_agent_toolkit.api import StripeAPI
except ImportError:
    StripeAPI = None

from models.entities.couchbase.agent_runs import (
    AgentRunData,
    ScoreBreakdown,
    TraceStep,
)
from models.entities.couchbase.listings import Listing
from models.entities.couchbase.orders import OrderLineItem
from models.entities.couchbase.users import BuyerProfile, User
from models.operations.agent_runs import (
    agent_run_append_step,
    agent_run_complete,
    agent_run_create,
    agent_run_fail,
)
from models.operations.listings import listing_get, listing_reserve_quantity, listing_search
from models.operations.orders import (
    order_create,
    order_set_payment_intent,
    order_set_payment_link,
    order_update_status,
)
from opentelemetry import trace as otel_trace

from utils import env, log

from agents.shared.base import check_no_running_run
from .budget import get_remaining_budget_eur
from .scorer import rank_listings

logger = log.get_logger(__name__)
tracer = otel_trace.get_tracer("carbonbridge.buyer_agent")

STRIPE_SECRET_KEY = env.EnvVarSpec(
    id="STRIPE_SECRET_KEY", is_optional=True, is_secret=True
)
GEMINI_API_KEY = env.EnvVarSpec(
    id="GEMINI_API_KEY", is_optional=True, is_secret=True
)
WEB_APP_URL = env.EnvVarSpec(
    id="WEB_APP_URL", is_optional=True, is_secret=False
)

# Default criteria values when buyer hasn't specified
DEFAULT_MONTHLY_BUDGET = 10000.0
DEFAULT_AUTO_APPROVE_UNDER = 5000.0
DEFAULT_MIN_VINTAGE_YEAR = 2020
DEFAULT_MAX_PRICE = 50.0


def _stripe_configured() -> bool:
    return StripeAPI is not None and bool(env.parse(STRIPE_SECRET_KEY))


# ---------------------------------------------------------------------------
# Structured output + dependency container
# ---------------------------------------------------------------------------

class AgentDecision(BaseModel):
    """Structured output from the buyer agent's reasoning."""
    action: str  # "purchase" | "propose" | "skip"
    listing_id: Optional[str] = None
    quantity_tonnes: Optional[float] = None
    total_cost_eur: Optional[float] = None
    rationale: str
    key_strengths: List[str] = []
    risks: List[str] = []


@dataclass
class BuyerAgentDeps:
    buyer_id: str
    buyer_profile: BuyerProfile
    criteria: dict
    remaining_budget_eur: float
    monthly_budget_eur: float
    auto_approve_under_eur: float
    max_price_eur: float
    min_vintage_year: int
    company_name: str = ""
    # Populated during tool calls
    listings_found: List[Listing] = field(default_factory=list)
    scores: List[ScoreBreakdown] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pydantic AI agent definition (Gemini 3 Flash)
# ---------------------------------------------------------------------------

def _build_agent() -> Agent[BuyerAgentDeps, AgentDecision]:
    """Construct the Pydantic AI agent with Gemini. Called once at module load."""

    agent = Agent(
        "google-gla:gemini-3-flash-preview",
        deps_type=BuyerAgentDeps,
        output_type=AgentDecision,
        system_prompt=(
            "You are an autonomous carbon credit purchasing agent for CarbonBridge, "
            "a voluntary carbon credit marketplace for SMEs. "
            "Your job is to find the best carbon credit listing for a buyer based on "
            "their criteria and budget, then decide whether to purchase, propose for "
            "approval, or skip.\n\n"
            "Follow this workflow:\n"
            "1. Call search_listings with the buyer's criteria to find available listings\n"
            "2. Call score_listings to rank the results\n"
            "3. If good matches exist, call select_best_match to pick the top listing\n"
            "4. Based on the total cost vs auto-approve threshold, decide the action:\n"
            "   - 'purchase' if cost <= auto_approve_under_eur\n"
            "   - 'propose' if cost > auto_approve_under_eur\n"
            "   - 'skip' if no suitable listings found or budget exhausted\n"
            "5. Return your decision with a clear, plain-English rationale\n\n"
            "Be concise. No jargon. Explain your reasoning as if talking to "
            "an SME owner who knows nothing about carbon markets."
        ),
    )

    @agent.system_prompt
    async def buyer_context(ctx: RunContext[BuyerAgentDeps]) -> str:
        d = ctx.deps
        preferred = d.criteria.get("preferred_types", [])
        co_benefits = d.criteria.get("preferred_co_benefits", [])
        return (
            f"Buyer: {d.company_name} (ID: {d.buyer_id})\n"
            f"Remaining monthly budget: EUR {d.remaining_budget_eur:.2f} "
            f"(of EUR {d.monthly_budget_eur:.2f})\n"
            f"Auto-approve threshold: EUR {d.auto_approve_under_eur:.2f}\n"
            f"Max price per tonne: EUR {d.max_price_eur:.2f}\n"
            f"Min vintage year: {d.min_vintage_year}\n"
            f"Preferred project types: {preferred or 'any'}\n"
            f"Preferred co-benefits: {co_benefits or 'any'}"
        )

    @agent.tool
    async def search_listings(
        ctx: RunContext[BuyerAgentDeps],
        max_price_eur: Optional[float] = None,
        project_type: Optional[str] = None,
        min_vintage_year: Optional[int] = None,
    ) -> dict:
        """Search active, verified carbon credit listings on the marketplace.

        Args:
            max_price_eur: Maximum price per tonne in EUR. Defaults to buyer's criteria.
            project_type: Filter by project type (afforestation, renewable, cookstoves, etc.)
            min_vintage_year: Minimum vintage year for credits.
        """
        price = max_price_eur if max_price_eur is not None else ctx.deps.max_price_eur
        listings = await listing_search(max_price=price, project_type=project_type, limit=50)

        # Filter: available quantity >= 1t
        listings = [
            lst for lst in listings
            if (lst.data.quantity_tonnes - lst.data.quantity_reserved - lst.data.quantity_sold) >= 1.0
        ]
        # Vintage minimum (listing_search uses exact match, so filter client-side)
        if min_vintage_year:
            listings = [lst for lst in listings if (lst.data.vintage_year or 0) >= min_vintage_year]

        ctx.deps.listings_found = listings
        return {
            "count": len(listings),
            "listings": [
                {
                    "id": lst.id,
                    "project_name": lst.data.project_name,
                    "project_type": lst.data.project_type,
                    "project_country": lst.data.project_country,
                    "vintage_year": lst.data.vintage_year,
                    "price_per_tonne_eur": lst.data.price_per_tonne_eur,
                    "quantity_available": round(
                        lst.data.quantity_tonnes - lst.data.quantity_reserved - lst.data.quantity_sold, 2
                    ),
                    "co_benefits": lst.data.co_benefits,
                    "verification_status": lst.data.verification_status,
                }
                for lst in listings
            ],
        }

    @agent.tool
    async def score_listings(ctx: RunContext[BuyerAgentDeps]) -> dict:
        """Score and rank the previously searched listings against buyer criteria."""
        if not ctx.deps.listings_found:
            return {"error": "No listings to score. Call search_listings first."}

        ranked = rank_listings(ctx.deps.listings_found, ctx.deps.criteria, ctx.deps.buyer_profile)
        ctx.deps.scores = [s for _, s in ranked]

        return {
            "ranked_count": len(ranked),
            "top_listings": [
                {
                    "listing_id": s.listing_id,
                    "total_score": s.total,
                    "project_type_match": s.project_type_match,
                    "price_score": s.price_score,
                    "vintage_score": s.vintage_score,
                    "co_benefit_score": s.co_benefit_score,
                    "verification_score": s.verification_score,
                }
                for _, s in ranked[:5]
            ],
        }

    @agent.tool
    async def select_best_match(ctx: RunContext[BuyerAgentDeps], listing_id: str) -> dict:
        """Get full details of a specific listing and calculate purchase quantity within budget.

        Args:
            listing_id: The ID of the listing to select.
        """
        listing = await listing_get(listing_id)
        if not listing:
            return {"error": f"Listing {listing_id} not found"}

        available = listing.data.quantity_tonnes - listing.data.quantity_reserved - listing.data.quantity_sold
        max_by_budget = ctx.deps.remaining_budget_eur / listing.data.price_per_tonne_eur
        quantity = round(min(available, max_by_budget), 2)

        if quantity < 1.0:
            return {
                "error": "Insufficient budget for minimum 1 tonne purchase",
                "remaining_budget_eur": ctx.deps.remaining_budget_eur,
                "price_per_tonne_eur": listing.data.price_per_tonne_eur,
            }

        total_cost = round(quantity * listing.data.price_per_tonne_eur, 2)
        return {
            "listing_id": listing.id,
            "project_name": listing.data.project_name,
            "project_type": listing.data.project_type,
            "project_country": listing.data.project_country,
            "vintage_year": listing.data.vintage_year,
            "price_per_tonne_eur": listing.data.price_per_tonne_eur,
            "quantity_tonnes": quantity,
            "total_cost_eur": total_cost,
            "co_benefits": listing.data.co_benefits,
            "auto_approve_under_eur": ctx.deps.auto_approve_under_eur,
            "within_auto_approve": total_cost <= ctx.deps.auto_approve_under_eur,
        }

    return agent


# Module-level agent instance
_buyer_agent = _build_agent()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_buyer_agent(
    buyer_id: str,
    trigger: Literal["manual", "scheduled", "threshold_exceeded"] = "manual",
) -> Optional[str]:
    """
    Execute the autonomous buyer agent for a single buyer.

    Returns the agent run ID, or None if skipped (e.g. already running).
    """
    if not await check_no_running_run(buyer_id, "autonomous_buyer"):
        return None

    step_idx = 0

    run_data = AgentRunData(
        agent_type="autonomous_buyer",
        owner_id=buyer_id,
        trigger_reason=trigger,
        status="running",
        triggered_at=datetime.now(timezone.utc),
    )
    run = await agent_run_create(run_data)
    run_id = run.id
    logger.info(f"Agent run {run_id} started for buyer {buyer_id} (trigger={trigger})")

    try:
        await _record_step(run_id, step_idx, "reasoning", "Agent run initialized", output={
            "run_id": run_id, "buyer_id": buyer_id, "trigger": trigger,
        })
        step_idx += 1

        # --- Load buyer profile ---
        start = time.monotonic()
        user = await User.get(buyer_id)
        if not user:
            raise ValueError(f"Buyer {buyer_id} not found")

        profile = user.data.buyer_profile
        criteria = (profile.autonomous_agent_criteria if profile else None) or {}
        monthly_budget = criteria.get("monthly_budget_eur", DEFAULT_MONTHLY_BUDGET)
        auto_approve_under = criteria.get("auto_approve_under_eur", DEFAULT_AUTO_APPROVE_UNDER)
        max_price = criteria.get("max_price_eur", DEFAULT_MAX_PRICE)
        min_vintage = criteria.get("min_vintage_year", DEFAULT_MIN_VINTAGE_YEAR)

        await _record_step(run_id, step_idx, "tool_call", "Loaded buyer profile and criteria",
            input_data={"buyer_id": buyer_id},
            output={
                "company": user.data.company_name,
                "monthly_budget_eur": monthly_budget,
                "auto_approve_under_eur": auto_approve_under,
                "max_price_eur": max_price,
                "preferred_types": criteria.get("preferred_types", []),
            },
            duration_ms=_elapsed(start),
        )
        step_idx += 1

        # --- Check budget ---
        start = time.monotonic()
        remaining = await get_remaining_budget_eur(buyer_id, monthly_budget)

        if remaining <= 0:
            await _record_step(run_id, step_idx, "reasoning", "Monthly budget exhausted",
                output={"remaining_eur": remaining, "monthly_budget_eur": monthly_budget},
                duration_ms=_elapsed(start),
            )
            await agent_run_complete(run_id, action_taken="skipped",
                selection_rationale="Monthly budget exhausted")
            return run_id

        await _record_step(run_id, step_idx, "reasoning", "Budget check passed",
            output={"remaining_eur": remaining, "monthly_budget_eur": monthly_budget},
            duration_ms=_elapsed(start),
        )
        step_idx += 1

        # --- Gemini-driven search, score, and selection ---
        deps = BuyerAgentDeps(
            buyer_id=buyer_id,
            buyer_profile=profile or BuyerProfile(),
            criteria=criteria,
            remaining_budget_eur=remaining,
            monthly_budget_eur=monthly_budget,
            auto_approve_under_eur=auto_approve_under,
            max_price_eur=max_price,
            min_vintage_year=min_vintage,
            company_name=user.data.company_name or "",
        )

        start = time.monotonic()
        await _record_step(run_id, step_idx, "reasoning", "Starting Gemini listing analysis",
            output={"model": "gemini-3-flash-preview"},
        )
        step_idx += 1

        with tracer.start_as_current_span("buyer_agent_run") as span:
            span.set_attribute("carbonbridge.run_id", run_id)
            span.set_attribute("carbonbridge.buyer_id", buyer_id)
            span.set_attribute("carbonbridge.trigger", trigger)
            result = await _buyer_agent.run(
                "Search for available carbon credit listings matching the buyer's criteria, "
                "score them, select the best match, and decide whether to purchase, propose "
                "for approval, or skip. Return your decision with a clear rationale.",
                deps=deps,
            )
        decision = result.output

        # Record Gemini's decision
        await _record_step(run_id, step_idx, "reasoning", "Gemini analysis complete",
            output={
                "action": decision.action,
                "listing_id": decision.listing_id,
                "quantity_tonnes": decision.quantity_tonnes,
                "total_cost_eur": decision.total_cost_eur,
                "rationale": decision.rationale,
            },
            listings_considered=[s.listing_id for s in deps.scores if s.listing_id],
            score_breakdown=next((s for s in deps.scores if s.listing_id == decision.listing_id), None),
            duration_ms=_elapsed(start),
        )
        step_idx += 1

        # Record "Selected best match" step (needed by approve endpoint)
        if decision.listing_id and decision.quantity_tonnes:
            listing = await listing_get(decision.listing_id)
            derived_price = (
                round(decision.total_cost_eur / decision.quantity_tonnes, 2)
                if decision.total_cost_eur and decision.quantity_tonnes else 0.0
            )
            await _record_step(run_id, step_idx, "decision", "Selected best match",
                output={
                    "listing_id": decision.listing_id,
                    "project_name": listing.data.project_name if listing else "unknown",
                    "quantity_tonnes": decision.quantity_tonnes,
                    "price_per_tonne_eur": listing.data.price_per_tonne_eur if listing else derived_price,
                    "total_cost_eur": decision.total_cost_eur,
                    "score": next((s.total for s in deps.scores if s.listing_id == decision.listing_id), 0.0),
                },
            )
            step_idx += 1

        # --- Act on decision ---
        if decision.action == "skip":
            await _record_step(run_id, step_idx, "decision", "Agent decided to skip",
                output={"rationale": decision.rationale},
            )
            await agent_run_complete(run_id, action_taken="skipped",
                selection_rationale=decision.rationale)
            return run_id

        if decision.action == "propose":
            await _record_step(run_id, step_idx, "decision",
                "Proposed for buyer approval (above auto-approve threshold)",
                output={
                    "listing_id": decision.listing_id,
                    "total_cost_eur": decision.total_cost_eur,
                    "auto_approve_under_eur": auto_approve_under,
                    "rationale": decision.rationale,
                },
            )
            await agent_run_complete(
                run_id,
                action_taken="proposed",
                status="awaiting_approval",
                final_selection_id=decision.listing_id,
                selection_rationale=decision.rationale,
                listings_shortlisted=[s.listing_id for s in deps.scores[:5] if s.listing_id],
            )
            return run_id

        # --- Purchase ---
        start = time.monotonic()
        if not decision.listing_id or not decision.quantity_tonnes or not decision.total_cost_eur:
            raise ValueError("Decision missing listing_id, quantity, or total_cost")

        listing = await listing_get(decision.listing_id)
        if not listing:
            raise ValueError(f"Listing {decision.listing_id} not found for purchase")

        reserved, reserve_err = await listing_reserve_quantity(decision.listing_id, decision.quantity_tonnes)
        if not reserved:
            raise RuntimeError(reserve_err)

        line_items = [
            OrderLineItem(
                listing_id=decision.listing_id,
                quantity=decision.quantity_tonnes,
                price_per_tonne=listing.data.price_per_tonne_eur,
                subtotal=decision.total_cost_eur,
            )
        ]
        order = await order_create(buyer_id, line_items, decision.total_cost_eur)

        # Payment via Stripe Agent Toolkit (Payment Link) or mock
        if _stripe_configured() and StripeAPI is not None:
            key = env.parse(STRIPE_SECRET_KEY)
            stripe_agent = StripeAPI(secret_key=key)
            web_app_url = env.parse(WEB_APP_URL) or "http://localhost:8000"

            # Create a Stripe Product + Price for this credit purchase
            product = stripe_agent.run(
                "create_product",
                name=f"Carbon Credits — {listing.data.project_name}",
                metadata={
                    "carbonbridge_order_id": order.id,
                    "listing_id": decision.listing_id,
                },
            )
            product_id = product.get("id") if isinstance(product, dict) else product

            price = stripe_agent.run(
                "create_price",
                product=product_id,
                unit_amount=int(listing.data.price_per_tonne_eur * 100),
                currency="eur",
            )
            price_id = price.get("id") if isinstance(price, dict) else price

            # Create Payment Link via Stripe Agent Toolkit
            payment_link = stripe_agent.run(
                "create_payment_link",
                line_items=[{"price": price_id, "quantity": int(decision.quantity_tonnes)}],
                metadata={
                    "carbonbridge_order_id": order.id,
                    "agent_run_id": run_id,
                    "buyer_id": buyer_id,
                },
                after_completion={
                    "type": "redirect",
                    "redirect": {"url": f"{web_app_url}/buyer/credits?order={order.id}"},
                },
            )
            payment_link_url = payment_link.get("url") if isinstance(payment_link, dict) else str(payment_link)
            payment_link_id = payment_link.get("id", "") if isinstance(payment_link, dict) else ""

            await order_set_payment_link(order.id, payment_link_url or "")
            await order_set_payment_intent(order.id, payment_link_id)
            payment_id = payment_link_id
            payment_mode = "stripe_agent_toolkit"
        else:
            mock_id = f"pi_agent_{hashlib.sha256(order.id.encode()).hexdigest()[:16]}"
            await order_set_payment_intent(order.id, mock_id)
            payment_id = mock_id
            payment_mode = "mock"
            payment_link_url = None

        order_status = "confirmed" if _stripe_configured() else "completed"
        await order_update_status(order.id, order_status)

        await _record_step(run_id, step_idx, "tool_call", "Created order and executed payment",
            output={
                "order_id": order.id,
                "payment_intent_id": payment_id,
                "payment_mode": payment_mode,
                "payment_link_url": payment_link_url,
                "total_eur": decision.total_cost_eur,
                "quantity_tonnes": decision.quantity_tonnes,
                "listing_id": decision.listing_id,
            },
            duration_ms=_elapsed(start),
        )
        step_idx += 1

        await _record_step(run_id, step_idx, "output", "Agent run completed successfully",
            output={"rationale": decision.rationale, "key_strengths": decision.key_strengths, "risks": decision.risks},
        )
        await agent_run_complete(
            run_id,
            action_taken="purchased",
            order_id=order.id,
            final_selection_id=decision.listing_id,
            selection_rationale=decision.rationale,
            listings_shortlisted=[s.listing_id for s in deps.scores[:5] if s.listing_id],
        )

        logger.info(f"Agent run {run_id}: purchased {decision.quantity_tonnes}t from {decision.listing_id} "
                     f"(order={order.id}, payment={payment_mode})")
        return run_id

    except Exception as e:
        logger.error(f"Agent run {run_id} failed: {e}", exc_info=True)
        await agent_run_fail(run_id, str(e))
        return run_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _elapsed(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


async def _record_step(
    run_id: str, step_index: int,
    step_type: Literal["tool_call", "reasoning", "decision", "output"],
    label: str,
    input_data=None, output=None, listings_considered=None,
    score_breakdown=None, duration_ms=None,
):
    """Convenience wrapper to append a TraceStep."""
    step = TraceStep(
        step_index=step_index, step_type=step_type, label=label,
        input=input_data, output=output, duration_ms=duration_ms,
        listings_considered=listings_considered or [],
        score_breakdown=score_breakdown,
    )
    await agent_run_append_step(run_id, step)
