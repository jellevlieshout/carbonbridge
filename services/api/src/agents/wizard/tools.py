"""
Pydantic AI tool implementations for the buyer wizard agent.

Tools call internal FastAPI endpoints (secured with INTERNAL_AGENT_API_KEY)
rather than importing Couchbase models directly; this keeps the agent layer
decoupled from the persistence layer and lets the tools be tested in isolation.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
from pydantic_ai import RunContext

from utils import log

logger = log.get_logger(__name__)

# ── Dependency injected into every tool ───────────────────────────────


@dataclass
class WizardDeps:
    """Dependencies injected into the Pydantic AI agent at call time."""

    buyer_id: str
    session_id: str
    internal_base_url: str  # e.g. "http://localhost:8000/api"
    api_key: str


# ── helpers ───────────────────────────────────────────────────────────


async def _post(
    deps: WizardDeps, path: str, body: Dict[str, Any]
) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(
            f"{deps.internal_base_url}{path}",
            json=body,
            headers={"X-Agent-API-Key": deps.api_key},
        )
        r.raise_for_status()
        return r.json()


async def _get(deps: WizardDeps, path: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(
            f"{deps.internal_base_url}{path}",
            headers={"X-Agent-API-Key": deps.api_key},
        )
        r.raise_for_status()
        return r.json()


# ── tool functions registered on the agent ────────────────────────────


async def tool_get_buyer_profile(ctx: RunContext[WizardDeps]) -> Dict[str, Any]:
    """
    Retrieve the saved buyer profile (sector, preferred project types, budget, etc.).
    Returns an empty dict if the buyer has no profile yet.
    """
    try:
        return await _get(ctx.deps, f"/internal/buyers/{ctx.deps.buyer_id}/profile")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {}
        raise
    except Exception as exc:
        logger.warning("get_buyer_profile failed: %s", exc)
        return {}


async def tool_estimate_footprint(
    ctx: RunContext[WizardDeps],
    sector: str,
    employees: int,
    country: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Estimate annual CO2 footprint from sector and headcount.
    Returns estimated_tonnes_low, estimated_tonnes_high, midpoint, and an
    explanation with a plain-language analogy.
    """
    payload: Dict[str, Any] = {"sector": sector, "employees": employees}
    if country:
        payload["country"] = country
    return await _post(ctx.deps, "/internal/footprint/estimate", payload)


async def tool_search_listings(
    ctx: RunContext[WizardDeps],
    project_type: Optional[str] = None,
    project_country: Optional[str] = None,
    max_price: Optional[float] = None,
    min_quantity: Optional[float] = None,
    vintage_year: Optional[int] = None,
    co_benefits: Optional[List[str]] = None,
    limit: int = 4,
) -> List[Dict[str, Any]]:
    """
    Search active, verified carbon credit listings matching the buyer's preferences.
    Returns up to `limit` listings sorted by date added.
    Each listing includes: id, project_name, project_type, project_country,
    price_per_tonne_eur, quantity_available, co_benefits, description.
    """
    payload: Dict[str, Any] = {"limit": limit}
    if project_type:
        payload["project_type"] = project_type
    if project_country:
        payload["project_country"] = project_country
    if max_price is not None:
        payload["max_price"] = max_price
    if min_quantity is not None:
        payload["min_quantity"] = min_quantity
    if vintage_year is not None:
        payload["vintage_year"] = vintage_year
    if co_benefits:
        payload["co_benefits"] = co_benefits

    data = await _post(ctx.deps, "/internal/listings/search", payload)
    return data.get("listings", [])


async def tool_get_listing_detail(
    ctx: RunContext[WizardDeps],
    listing_id: str,
) -> Dict[str, Any]:
    """
    Retrieve full detail for a single listing by its ID.
    Use this when the buyer asks for more information about a specific option.
    """
    return await _get(ctx.deps, f"/internal/listings/{listing_id}")


async def tool_create_order_draft(
    ctx: RunContext[WizardDeps],
    listing_id: str,
    quantity: float,
) -> Dict[str, Any]:
    """
    Create a pending order draft for the buyer.
    Reserves quantity on the listing atomically.
    Returns order_id, status, line_items, and total_eur.
    """
    payload = {
        "buyer_id": ctx.deps.buyer_id,
        "line_items": [{"listing_id": listing_id, "quantity": quantity}],
    }
    return await _post(ctx.deps, "/internal/orders/draft", payload)
