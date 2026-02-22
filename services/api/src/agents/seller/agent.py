"""
Seller advisory agent orchestration (Pydantic AI + Gemini).

A Pydantic AI agent triggered on demand (or on listing publication).
Loads the seller's listings, fetches market context from OffsetsDB,
scores competitive position, and generates actionable recommendations.
Returns a complete JSON report stored in an AgentRun document.  (Spec section 6.4)

Pipeline:
  load_seller_listings → fetch_market_context → score_competitive_position
    → generate_recommendations → write_agent_run
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from models.entities.couchbase.agent_runs import (
    AgentRunData,
    TraceStep,
)
from models.entities.couchbase.listings import Listing
from models.entities.couchbase.offsets_db_projects import OffsetsDBProject
from models.entities.couchbase.users import User
from models.operations.agent_runs import (
    agent_run_append_step,
    agent_run_complete,
    agent_run_create,
    agent_run_fail,
)
from models.operations.listings import listing_get_by_seller
from opentelemetry import trace as otel_trace

from utils import env, log

from agents.shared.base import check_no_running_run
from conf import SELLER_MODEL

logger = log.get_logger(__name__)
tracer = otel_trace.get_tracer("carbonbridge.seller_agent")


# ---------------------------------------------------------------------------
# Structured output + dependency container
# ---------------------------------------------------------------------------

class SellerRecommendation(BaseModel):
    """A single recommendation for one of the seller's listings."""
    listing_id: str
    recommendation_type: str  # "price_adjustment" | "highlight_co_benefits" | "vintage_note" | "competitive_strength"
    summary: str
    details: str
    suggested_price_eur: Optional[float] = None


class SellerAdvisoryDecision(BaseModel):
    """Structured output from the seller advisory agent."""
    overall_assessment: str
    recommendations: List[SellerRecommendation]
    market_position: str  # "underpriced" | "competitive" | "overpriced"
    key_strengths: List[str] = []
    risks: List[str] = []


@dataclass
class SellerAgentDeps:
    seller_id: str
    company_name: str
    # Populated during tool calls
    listings: List[Listing] = field(default_factory=list)
    market_projects: List[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pydantic AI agent definition (Gemini 3 Flash)
# ---------------------------------------------------------------------------

def _build_agent() -> Agent[SellerAgentDeps, SellerAdvisoryDecision]:
    """Construct the seller advisory Pydantic AI agent. Called once at module load."""

    agent = Agent(
        env.parse(SELLER_MODEL),
        deps_type=SellerAgentDeps,
        output_type=SellerAdvisoryDecision,
        system_prompt=(
            "You are a seller advisory agent for CarbonBridge, a voluntary carbon "
            "credit marketplace for SMEs. Your job is to analyze a seller's carbon "
            "credit listings against current market conditions from CarbonPlan's "
            "OffsetsDB and provide actionable recommendations.\n\n"
            "Follow this workflow:\n"
            "1. Call load_seller_listings to see the seller's current listings\n"
            "2. Call fetch_market_context with relevant project types and countries "
            "from the listings\n"
            "3. Call score_competitive_position to compare the seller's listings "
            "against the market\n"
            "4. Based on the analysis, return your advisory with specific, actionable "
            "recommendations per listing\n\n"
            "Be concise and business-focused. Explain your reasoning in plain English "
            "that a small business owner would understand. Focus on practical actions "
            "the seller can take to improve their listings."
        ),
    )

    @agent.system_prompt
    async def seller_context(ctx: RunContext[SellerAgentDeps]) -> str:
        d = ctx.deps
        return (
            f"Seller: {d.company_name} (ID: {d.seller_id})\n"
            f"Number of listings loaded: {len(d.listings)}"
        )

    @agent.tool
    async def load_seller_listings(ctx: RunContext[SellerAgentDeps]) -> dict:
        """Load all listings belonging to the current seller.

        Returns a summary of each listing including project details, pricing,
        quantity, and status.
        """
        all_listings = await listing_get_by_seller(ctx.deps.seller_id)
        # Only advise on actionable listings (not drafts or sold-out)
        listings = [lst for lst in all_listings if lst.data.status in ("active", "paused")]
        ctx.deps.listings = listings

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
                    "quantity_tonnes": lst.data.quantity_tonnes,
                    "co_benefits": lst.data.co_benefits,
                    "verification_status": lst.data.verification_status,
                    "status": lst.data.status,
                    "registry_name": lst.data.registry_name,
                }
                for lst in listings
            ],
        }

    @agent.tool
    async def fetch_market_context(
        ctx: RunContext[SellerAgentDeps],
        project_type: Optional[str] = None,
        country: Optional[str] = None,
    ) -> dict:
        """Fetch market context from CarbonPlan's OffsetsDB for comparable projects.

        Args:
            project_type: Filter by project type (e.g. "afforestation", "renewable").
            country: Filter by country (e.g. "Brazil", "India").
        """
        # Direct N1QL query against offsets_db_project collection
        keyspace = OffsetsDBProject.get_keyspace()
        conditions = ["1=1"]
        params: Dict[str, str] = {}

        if project_type:
            conditions.append("project_type = $project_type")
            params["project_type"] = project_type
        if country:
            conditions.append("country = $country")
            params["country"] = country

        where = " AND ".join(conditions)
        collection_name = OffsetsDBProject._collection_name
        query = (
            f"SELECT META().id, * FROM {keyspace} "
            f"WHERE {where} "
            f"ORDER BY total_credits_issued DESC "
            f"LIMIT 20"
        )

        try:
            rows = await keyspace.query(query, **params)
        except Exception as e:
            logger.warning(f"OffsetsDB market context query failed: {e}")
            return {"projects": [], "total": 0}

        projects = []
        for row in rows:
            data = row.get(collection_name, row)
            if isinstance(data, dict):
                project = {
                    "offsets_db_project_id": data.get("offsets_db_project_id", row.get("id", "")),
                    "name": data.get("name"),
                    "registry": data.get("registry"),
                    "category": data.get("category"),
                    "country": data.get("country"),
                    "total_credits_issued": data.get("total_credits_issued"),
                    "total_credits_retired": data.get("total_credits_retired"),
                    "status": data.get("status"),
                }
                projects.append(project)

        ctx.deps.market_projects.extend(projects)

        return {"projects": projects, "total": len(projects)}

    @agent.tool
    async def score_competitive_position(ctx: RunContext[SellerAgentDeps]) -> dict:
        """Score the seller's listings against the fetched market context.

        Compares pricing, vintage years, and project type demand against
        OffsetsDB market data. Must be called after load_seller_listings
        and fetch_market_context.
        """
        if not ctx.deps.listings:
            return {"error": "No listings loaded. Call load_seller_listings first."}
        if not ctx.deps.market_projects:
            return {"error": "No market context loaded. Call fetch_market_context first."}

        # Aggregate market stats from OffsetsDB data
        market_by_type: Dict[str, List[dict]] = {}
        for p in ctx.deps.market_projects:
            cat = p.get("category", "Other") or "Other"
            market_by_type.setdefault(cat, []).append(p)

        # Compute market-level stats
        market_stats = {}
        for cat, projects in market_by_type.items():
            total_issued = sum(p.get("total_credits_issued", 0) or 0 for p in projects)
            total_retired = sum(p.get("total_credits_retired", 0) or 0 for p in projects)
            retirement_rate = (total_retired / total_issued * 100) if total_issued > 0 else 0
            market_stats[cat] = {
                "project_count": len(projects),
                "total_credits_issued": round(total_issued, 2),
                "total_credits_retired": round(total_retired, 2),
                "retirement_rate_pct": round(retirement_rate, 1),
            }

        # Score each listing
        listing_scores = []
        for listing in ctx.deps.listings:
            available = listing.data.quantity_tonnes - listing.data.quantity_reserved - listing.data.quantity_sold

            # Find matching market category
            # Map listing project_type to OffsetsDB categories
            type_to_category = {
                "afforestation": "Forest",
                "renewable": "Renewable Energy",
                "cookstoves": "Energy Efficiency",
                "methane_capture": "GHG Management",
                "fuel_switching": "Fuel Switching",
                "energy_efficiency": "Energy Efficiency",
                "agriculture": "Agriculture",
                "other": "Other",
            }
            category = type_to_category.get(listing.data.project_type, "Other")
            cat_stats = market_stats.get(category, {})

            listing_scores.append({
                "listing_id": listing.id,
                "project_name": listing.data.project_name,
                "project_type": listing.data.project_type,
                "mapped_category": category,
                "price_per_tonne_eur": listing.data.price_per_tonne_eur,
                "quantity_available": round(available, 2),
                "vintage_year": listing.data.vintage_year,
                "co_benefits": listing.data.co_benefits,
                "verification_status": listing.data.verification_status,
                "market_category_stats": cat_stats,
            })

        return {
            "listing_scores": listing_scores,
            "market_stats": market_stats,
            "total_market_projects_analyzed": len(ctx.deps.market_projects),
        }

    return agent


# Module-level agent instance
_seller_agent = _build_agent()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_seller_advisory_agent(
    seller_id: str,
    trigger: Literal["manual", "scheduled", "threshold_exceeded"] = "manual",
) -> Optional[str]:
    """
    Execute the seller advisory agent for a single seller.

    Returns the agent run ID, or None if skipped (e.g. already running).
    """
    if not await check_no_running_run(seller_id, "seller_advisory"):
        return None

    step_idx = 0

    run_data = AgentRunData(
        agent_type="seller_advisory",
        owner_id=seller_id,
        trigger_reason=trigger,
        status="running",
        triggered_at=datetime.now(timezone.utc),
    )
    run = await agent_run_create(run_data)
    run_id = run.id
    logger.info(f"Seller advisory run {run_id} started for seller {seller_id} (trigger={trigger})")

    try:
        await _record_step(run_id, step_idx, "reasoning", "Agent run initialized", output={
            "run_id": run_id, "seller_id": seller_id, "trigger": trigger,
        })
        step_idx += 1

        # --- Load seller profile ---
        start = time.monotonic()
        user = await User.get(seller_id)
        if not user:
            raise ValueError(f"Seller {seller_id} not found")

        company_name = user.data.company_name or ""

        await _record_step(run_id, step_idx, "tool_call", "Loaded seller profile",
            input_data={"seller_id": seller_id},
            output={"company": company_name, "role": user.data.role},
            duration_ms=_elapsed(start),
        )
        step_idx += 1

        # --- Gemini-driven analysis pipeline ---
        deps = SellerAgentDeps(
            seller_id=seller_id,
            company_name=company_name,
        )

        start = time.monotonic()
        await _record_step(run_id, step_idx, "reasoning", "Starting Gemini listing analysis",
            output={"model": "gemini-2.5-flash"},
        )
        step_idx += 1

        with tracer.start_as_current_span("seller_advisory_run") as span:
            span.set_attribute("carbonbridge.run_id", run_id)
            span.set_attribute("carbonbridge.seller_id", seller_id)
            span.set_attribute("carbonbridge.trigger", trigger)
            result = await _seller_agent.run(
                "Load the seller's listings, fetch market context for relevant project "
                "types and countries, score the competitive position, and generate "
                "actionable recommendations. Return your advisory with specific "
                "recommendations per listing.",
                deps=deps,
            )
        decision = result.output

        # Record Gemini's analysis
        await _record_step(run_id, step_idx, "reasoning", "Gemini analysis complete",
            output={
                "overall_assessment": decision.overall_assessment,
                "market_position": decision.market_position,
                "recommendation_count": len(decision.recommendations),
                "key_strengths": decision.key_strengths,
                "risks": decision.risks,
            },
            listings_considered=[lst.id for lst in deps.listings],
            duration_ms=_elapsed(start),
        )
        step_idx += 1

        # Record individual recommendations
        await _record_step(run_id, step_idx, "decision", "Advisory recommendations generated",
            output={
                "recommendations": [
                    {
                        "listing_id": r.listing_id,
                        "type": r.recommendation_type,
                        "summary": r.summary,
                        "details": r.details,
                        "suggested_price_eur": r.suggested_price_eur,
                    }
                    for r in decision.recommendations
                ],
            },
        )
        step_idx += 1

        # Final output step
        await _record_step(run_id, step_idx, "output", "Advisory complete",
            output={
                "overall_assessment": decision.overall_assessment,
                "market_position": decision.market_position,
                "key_strengths": decision.key_strengths,
                "risks": decision.risks,
            },
        )

        await agent_run_complete(
            run_id,
            action_taken="recommendations_generated",
            selection_rationale=decision.overall_assessment,
            listings_shortlisted=[lst.id for lst in deps.listings],
        )

        logger.info(
            f"Seller advisory run {run_id}: {len(decision.recommendations)} recommendations "
            f"generated for {len(deps.listings)} listings (position={decision.market_position})"
        )
        return run_id

    except Exception as e:
        logger.error(f"Seller advisory run {run_id} failed: {e}", exc_info=True)
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
