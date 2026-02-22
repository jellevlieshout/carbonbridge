"""
Pydantic AI tool implementations for the buyer wizard agent.

Tools call model operations directly (in-process) — no HTTP, no special API
keys. Authentication is handled at the HTTP layer when the wizard route is
invoked, so the agent inherits the caller's identity and can trust its
buyer_id/session_id context.

Data sources:
- Emissions: UK DEFRA, US EPA, European Environment Agency sector benchmarks
- Pricing: Ecosystem Marketplace 2024, AlliedOffsets 2025, ClimateFocus VCM 2024
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pydantic_ai import RunContext
from utils import log

logger = log.get_logger(__name__)

# ── Footprint estimation lookup table ─────────────────────────────────
# Tonnes CO2e per employee per year by sector.
# Sources: UK DEFRA 2023, EPA GHG Calculator, EEA sector benchmarks, ESG reporting data.
# (low, high) — midpoint used for estimate.

_FOOTPRINT_PER_EMPLOYEE: Dict[str, tuple[float, float]] = {
    # Knowledge / office-based
    "technology":      (2.0,  5.0),
    "software":        (2.0,  4.5),
    "it":              (2.0,  5.0),
    "marketing":       (2.5,  6.0),
    "consulting":      (3.0,  7.0),
    "finance":         (3.0,  7.0),
    "banking":         (3.5,  8.0),
    "legal":           (2.5,  5.5),
    "insurance":       (2.5,  6.0),
    "media":           (2.0,  5.0),
    "design":          (2.0,  4.5),
    "accounting":      (2.0,  5.0),

    # Public services / education / health
    "healthcare":      (4.0,  9.0),
    "hospital":        (5.0, 11.0),
    "education":       (2.0,  5.0),
    "government":      (2.5,  6.0),
    "ngo":             (2.0,  5.0),

    # Retail / hospitality / food
    "retail":          (4.0,  9.0),
    "e-commerce":      (3.0,  7.0),
    "ecommerce":       (3.0,  7.0),
    "hospitality":     (5.0, 12.0),
    "hotel":           (5.0, 13.0),
    "restaurant":      (4.0, 10.0),
    "food_beverage":   (5.0, 12.0),
    "food":            (5.0, 12.0),
    "beverage":        (4.5, 10.0),
    "tourism":         (6.0, 14.0),

    # Construction / real estate
    "construction":    (8.0, 18.0),
    "real_estate":     (3.0,  7.0),
    "architecture":    (3.0,  7.0),
    "engineering":     (4.0,  9.0),

    # Manufacturing / industry
    "manufacturing":   (8.0, 20.0),
    "chemicals":       (12.0, 28.0),
    "pharmaceutical":  (7.0, 16.0),
    "textiles":        (6.0, 14.0),
    "electronics":     (5.0, 12.0),
    "automotive":      (10.0, 22.0),
    "aerospace":       (12.0, 28.0),
    "mining":          (12.0, 35.0),
    "steel":           (15.0, 40.0),
    "cement":          (18.0, 45.0),

    # Energy / utilities
    "energy":          (10.0, 30.0),
    "utilities":       (8.0, 20.0),
    "oil_gas":         (15.0, 40.0),
    "renewable_energy": (3.0,  8.0),

    # Transport / logistics
    "logistics":       (10.0, 25.0),
    "transport":       (10.0, 25.0),
    "shipping":        (12.0, 30.0),
    "aviation":        (20.0, 50.0),
    "trucking":        (12.0, 28.0),

    # Agriculture / forestry
    "agriculture":     (6.0, 15.0),
    "farming":         (6.0, 15.0),
    "forestry":        (3.0,  8.0),
    "fishing":         (5.0, 12.0),
    "food_production": (7.0, 18.0),
    "waste_management": (5.0, 12.0),
}

_DEFAULT_FOOTPRINT = (3.0, 8.0)

# ── Analogies (tonnes → plain-language comparison) ────────────────────
_ANALOGIES: list[tuple[float, str]] = [
    (0.5,  "roughly equivalent to one transatlantic return flight per employee"),
    (1.0,  "about the same as one return economy flight from London to New York"),
    (3.0,  "comparable to heating an average European home for a year"),
    (5.0,  "like the annual energy use of an average EU household"),
    (10.0, "equivalent to driving a petrol car roughly 40,000 km"),
    (25.0, "similar to the annual footprint of 2–3 European households combined"),
    (50.0, "comparable to 5 average European households' annual emissions"),
    (100.0, "like running a small petrol-powered factory for a year"),
]

# ── Realistic price ranges by project type (EUR/tonne, 2024–2025 data) ─
# Sources: Ecosystem Marketplace 2024, AlliedOffsets 2025, ClimateFocus VCM review
PROJECT_PRICE_RANGES: Dict[str, Dict[str, float]] = {
    "afforestation":      {"min": 8.0,  "typical": 18.0, "max": 45.0},
    "renewable":          {"min": 2.5,  "typical":  7.0, "max": 20.0},
    "cookstoves":         {"min": 4.0,  "typical": 12.0, "max": 30.0},
    "methane_capture":    {"min": 3.0,  "typical":  9.0, "max": 25.0},
    "fuel_switching":     {"min": 3.0,  "typical":  8.0, "max": 20.0},
    "energy_efficiency":  {"min": 2.5,  "typical":  7.0, "max": 18.0},
    "agriculture":        {"min": 4.0,  "typical": 11.0, "max": 28.0},
    "other":              {"min": 3.0,  "typical":  8.0, "max": 20.0},
}

# ── Project type plain-language descriptions (for agent responses) ─────
PROJECT_DESCRIPTIONS: Dict[str, str] = {
    "afforestation":     "Planting and restoring forests — absorbs CO2 and supports biodiversity",
    "renewable":         "Funding wind and solar projects that replace fossil fuels",
    "cookstoves":        "Replacing open fires with clean cookstoves in rural communities — cuts indoor air pollution too",
    "methane_capture":   "Capturing methane from landfills or agriculture before it reaches the atmosphere",
    "fuel_switching":    "Helping communities switch from dirty fuels to cleaner alternatives",
    "energy_efficiency": "Improving building insulation and industrial processes to waste less energy",
    "agriculture":       "Supporting sustainable farming that stores carbon in soil",
    "other":             "Other verified emissions-reduction projects",
}


# ── Dependencies ──────────────────────────────────────────────────────


@dataclass
class WizardDeps:
    """Context passed from the wizard runner into every agent tool call."""

    buyer_id: str
    session_id: str


# ── Tool implementations ──────────────────────────────────────────────


async def tool_get_buyer_profile(ctx: RunContext[WizardDeps]) -> Dict[str, Any]:
    """
    Retrieve the saved buyer profile (sector, preferred project types, budget, etc.)
    AND user-level company data (company_name, country, role).
    Returns an empty dict if the buyer has no profile yet.
    Call this at the start of every session to check what is already known.
    """
    try:
        from models.operations.users import user_get_data_for_frontend

        data = await user_get_data_for_frontend(ctx.deps.buyer_id)
        user = data.get("user", {})
        result: Dict[str, Any] = {
            "company_name": user.get("company_name"),
            "sector": user.get("sector"),
            "country": user.get("country"),
            "company_size_employees": user.get("company_size_employees"),
            "role": user.get("role"),
        }
        bp = user.get("buyer_profile") or {}
        result.update({
            "annual_co2_tonnes_estimate": bp.get("annual_co2_tonnes_estimate"),
            "primary_offset_motivation": bp.get("primary_offset_motivation"),
            "preferred_project_types": bp.get("preferred_project_types") or [],
            "preferred_regions": bp.get("preferred_regions") or [],
            "budget_per_tonne_max_eur": bp.get("budget_per_tonne_max_eur"),
        })
        return {k: v for k, v in result.items() if v is not None and v != []}
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
    Always call this tool before presenting a footprint estimate — do not guess.
    """
    # Normalise sector string to lookup key
    sector_key = (
        sector.lower()
        .strip()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        .replace("&", "_")
    )

    # Try exact match first, then prefix match for compound sector names
    per_emp = _FOOTPRINT_PER_EMPLOYEE.get(sector_key)
    if per_emp is None:
        for key in _FOOTPRINT_PER_EMPLOYEE:
            if sector_key.startswith(key) or key.startswith(sector_key):
                per_emp = _FOOTPRINT_PER_EMPLOYEE[key]
                break
    if per_emp is None:
        per_emp = _DEFAULT_FOOTPRINT

    per_emp_low, per_emp_high = per_emp

    low = round(per_emp_low * employees, 1)
    high = round(per_emp_high * employees, 1)
    mid = round((low + high) / 2, 1)

    analogy = ""
    for threshold, text in reversed(_ANALOGIES):
        if mid >= threshold:
            analogy = f" That's {text}."
            break

    explanation = (
        f"Based on {sector} sector benchmarks with {employees} employees, "
        f"we estimate your annual carbon footprint is roughly {low:.0f}–{high:.0f} tonnes CO2e "
        f"(midpoint {mid:.0f} tonnes per year).{analogy}"
    )

    # Suggest a reasonable offset budget based on typical market prices
    typical_total_low = round(mid * 5.0, 0)   # €5/tonne lower bound
    typical_total_high = round(mid * 20.0, 0)  # €20/tonne upper estimate

    return {
        "estimated_tonnes_low": low,
        "estimated_tonnes_high": high,
        "midpoint": mid,
        "explanation": explanation,
        "typical_cost_range_eur": f"€{typical_total_low:.0f}–€{typical_total_high:.0f}",
        "note": (
            "Prices vary €3–€45/tonne depending on project type. "
            "Forestry and removal projects cost more; renewable energy credits are cheaper."
        ),
    }


async def tool_search_listings(
    ctx: RunContext[WizardDeps],
    project_type: Optional[str] = None,
    project_country: Optional[str] = None,
    max_price: Optional[float] = None,
    min_quantity: Optional[float] = None,
    vintage_year: Optional[int] = None,
    co_benefits: Optional[List[str]] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    """
    Search active, verified carbon credit listings matching the buyer's preferences.
    Returns a dict with:
      - listings: list of matching listings (may be empty)
      - total: count of results
      - listings_found: bool — False when no results (use this to trigger no-match flow)
    Each listing includes: id, project_name, project_type, project_country,
    price_per_tonne_eur, quantity_available, co_benefits, description.
    If listings_found is False, you MUST ask the buyer whether they want the
    autonomous agent to monitor the market and buy on their behalf when matching
    credits become available.
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
            "vintage_year": item.data.vintage_year,
            "verification_status": item.data.verification_status,
        }
        for item in results
        if (item.data.quantity_tonnes - item.data.quantity_reserved - item.data.quantity_sold) >= 0.5
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
        "registry_name": d.registry_name,
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
    Only call this after the buyer has explicitly confirmed which listing
    they want and the quantity.
    """
    from models.entities.couchbase.orders import OrderLineItem
    from models.operations.listings import listing_get, listing_reserve_quantity
    from models.operations.orders import order_create

    listing = await listing_get(listing_id)
    if not listing:
        return {"error": f"Listing {listing_id} not found"}

    if listing.data.status != "active":
        return {"error": f"Listing {listing_id} is not active"}

    reserved, err = await listing_reserve_quantity(listing_id, quantity)
    if not reserved:
        return {"error": err}

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
        "project_name": listing.data.project_name,
        "project_type": listing.data.project_type,
        "price_per_tonne_eur": listing.data.price_per_tonne_eur,
        "quantity_tonnes": quantity,
    }
