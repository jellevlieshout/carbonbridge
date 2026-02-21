"""
Pydantic AI tool implementations for the buyer wizard agent.

Tools call model operations directly (in-process) — no HTTP, no special API
keys. Authentication is handled at the HTTP layer when the wizard route is
invoked, so the agent inherits the caller's identity and can trust its
buyer_id/session_id context.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pydantic_ai import RunContext
from utils import log

logger = log.get_logger(__name__)

# ── Footprint estimation lookup table ─────────────────────────────────
# Tonnes CO2e per employee per year by sector.
# Sources: UK DEFRA, EPA, various ESG reporting benchmarks (simplified).

_FOOTPRINT_PER_EMPLOYEE: Dict[str, tuple[float, float]] = {
    "technology":    (2.0,  5.0),
    "software":      (2.0,  5.0),
    "marketing":     (2.5,  6.0),
    "consulting":    (3.0,  7.0),
    "finance":       (3.0,  7.0),
    "legal":         (2.5,  5.5),
    "healthcare":    (4.0,  8.0),
    "education":     (2.0,  5.0),
    "retail":        (4.0,  9.0),
    "hospitality":   (5.0, 12.0),
    "manufacturing": (8.0, 20.0),
    "logistics":     (10.0, 25.0),
    "transport":     (10.0, 25.0),
    "construction":  (8.0, 18.0),
    "agriculture":   (6.0, 15.0),
    "energy":        (10.0, 30.0),
    "mining":        (12.0, 35.0),
    "food_beverage": (5.0, 12.0),
    "real_estate":   (3.0,  7.0),
}

_DEFAULT_FOOTPRINT = (3.0, 8.0)

_ANALOGIES = [
    (1.0,  "roughly one return economy flight from London to New York"),
    (5.0,  "about the same as heating an average UK home for a year"),
    (10.0, "equivalent to driving a petrol car about 40,000 km"),
    (50.0, "comparable to the annual emissions of about 5 average European households"),
]


# ── Dependencies ──────────────────────────────────────────────────────


@dataclass
class WizardDeps:
    """Context passed from the wizard runner into every agent tool call."""

    buyer_id: str
    session_id: str


# ── Tool implementations ──────────────────────────────────────────────


async def tool_get_buyer_profile(ctx: RunContext[WizardDeps]) -> Dict[str, Any]:
    """
    Retrieve the saved buyer profile (sector, preferred project types, budget, etc.).
    Returns an empty dict if the buyer has no profile yet.
    """
    try:
        from models.operations.users import user_get_buyer_profile

        profile = await user_get_buyer_profile(ctx.deps.buyer_id)
        if not profile:
            return {}
        return profile.model_dump()
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
    sector_key = sector.lower().replace(" ", "_").replace("-", "_")
    per_emp_low, per_emp_high = _FOOTPRINT_PER_EMPLOYEE.get(sector_key, _DEFAULT_FOOTPRINT)

    low = round(per_emp_low * employees, 1)
    high = round(per_emp_high * employees, 1)
    mid = round((low + high) / 2, 1)

    analogy = ""
    for threshold, text in reversed(_ANALOGIES):
        if mid >= threshold:
            analogy = f" That's {text}."
            break

    explanation = (
        f"Based on the {sector} sector with {employees} employees, "
        f"we estimate your annual footprint is roughly {low:.0f}–{high:.0f} tonnes CO2e "
        f"(midpoint {mid:.0f} tonnes).{analogy}"
    )
    return {
        "estimated_tonnes_low": low,
        "estimated_tonnes_high": high,
        "midpoint": mid,
        "explanation": explanation,
    }


async def tool_search_listings(
    ctx: RunContext[WizardDeps],
    project_type: Optional[str] = None,
    project_country: Optional[str] = None,
    max_price: Optional[float] = None,
    min_quantity: Optional[float] = None,
    vintage_year: Optional[int] = None,
    co_benefits: Optional[List[str]] = None,
    limit: int = 4,
) -> Dict[str, Any]:
    """
    Search active, verified carbon credit listings matching the buyer's preferences.
    Returns a dict with:
      - listings: list of matching listings (may be empty)
      - total: count of results
      - listings_found: bool — False when no results (use this to trigger no-match flow)
    Each listing includes: id, project_name, project_type, project_country,
    price_per_tonne_eur, quantity_available, co_benefits, description.
    """
    try:
        from models.operations.listings import listing_search

        results = await listing_search(
            project_type=project_type,
            project_country=project_country,
            max_price=max_price,
            min_quantity=min_quantity,
            vintage_year=vintage_year,
            limit=limit,
        )
    except Exception as exc:
        logger.warning("tool_search_listings failed: %s", exc)
        return {"listings": [], "total": 0, "listings_found": False, "error": str(exc)}

    if co_benefits:
        requested = {b.lower() for b in co_benefits}
        results = [
            r for r in results
            if requested & {b.lower() for b in r.data.co_benefits}
        ]

    items = [
        {
            "id": item.id,
            "project_name": item.data.project_name,
            "project_type": item.data.project_type,
            "project_country": item.data.project_country,
            "price_per_tonne_eur": item.data.price_per_tonne_eur,
            "quantity_available": round(
                item.data.quantity_tonnes
                - item.data.quantity_reserved
                - item.data.quantity_sold,
                2,
            ),
            "co_benefits": item.data.co_benefits,
            "description": item.data.description,
        }
        for item in results
    ]

    return {
        "listings": items,
        "total": len(items),
        "listings_found": len(items) > 0,
    }


async def tool_get_listing_detail(
    ctx: RunContext[WizardDeps],
    listing_id: str,
) -> Dict[str, Any]:
    """
    Retrieve full detail for a single listing by its ID.
    Use this when the buyer asks for more information about a specific option.
    """
    from models.operations.listings import listing_get

    listing = await listing_get(listing_id)
    if not listing:
        return {}
    d = listing.data
    return {
        "id": listing.id,
        "project_name": d.project_name,
        "project_type": d.project_type,
        "project_country": d.project_country,
        "vintage_year": d.vintage_year,
        "price_per_tonne_eur": d.price_per_tonne_eur,
        "quantity_available": round(
            d.quantity_tonnes - d.quantity_reserved - d.quantity_sold, 2
        ),
        "methodology": d.methodology,
        "co_benefits": d.co_benefits,
        "description": d.description,
        "verification_status": d.verification_status,
    }


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
    from models.entities.couchbase.orders import OrderLineItem
    from models.operations.listings import listing_get, listing_reserve_quantity
    from models.operations.orders import order_create

    listing = await listing_get(listing_id)
    if not listing:
        return {"error": f"Listing {listing_id} not found"}

    if listing.data.status != "active":
        return {"error": f"Listing {listing_id} is not active"}

    available = round(
        listing.data.quantity_tonnes
        - listing.data.quantity_reserved
        - listing.data.quantity_sold,
        2,
    )
    if quantity > available:
        return {"error": f"Only {available}t available on listing {listing_id}"}

    reserved = await listing_reserve_quantity(listing_id, quantity)
    if not reserved:
        return {"error": f"Could not reserve {quantity}t on listing {listing_id}"}

    subtotal = round(quantity * listing.data.price_per_tonne_eur, 2)
    line_item = OrderLineItem(
        listing_id=listing_id,
        quantity=quantity,
        price_per_tonne=listing.data.price_per_tonne_eur,
        subtotal=subtotal,
    )
    order = await order_create(ctx.deps.buyer_id, [line_item], subtotal)

    return {
        "order_id": order.id,
        "status": order.data.status,
        "line_items": [li.model_dump() for li in order.data.line_items],
        "total_eur": order.data.total_eur,
    }
