"""
Internal tool endpoints consumed by Pydantic AI agents.
Secured with INTERNAL_AGENT_API_KEY, not exposed publicly.
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from utils import env, log

from models.entities.couchbase.orders import OrderLineItem
from models.operations.listings import listing_get, listing_search, listing_update
from models.operations.orders import (
    order_create,
    order_get,
    order_record_ledger_entries,
    order_set_payment_intent,
    order_update_payment_status,
    order_update_status,
)
from models.operations.users import user_get_buyer_profile

logger = log.get_logger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])

# ---------------------------------------------------------------------------
# Auth: API key guard
# ---------------------------------------------------------------------------

INTERNAL_AGENT_API_KEY = env.EnvVarSpec(
    id="INTERNAL_AGENT_API_KEY", is_optional=True, is_secret=True
)


async def require_agent_api_key(
    x_agent_api_key: Optional[str] = Header(None, alias="X-Agent-API-Key"),
):
    expected = env.parse(INTERNAL_AGENT_API_KEY)
    if not expected:
        # No key configured — allow all internal callers (dev / hackathon mode)
        return
    if x_agent_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent API key",
        )


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class ListingSearchRequest(BaseModel):
    project_type: Optional[str] = None
    project_country: Optional[str] = None
    max_price: Optional[float] = None
    min_quantity: Optional[float] = None
    vintage_year: Optional[int] = None
    co_benefits: Optional[List[str]] = None
    limit: int = 10
    offset: int = 0


class ListingResult(BaseModel):
    id: str
    seller_id: str
    registry_name: str
    project_name: str
    project_type: str
    project_country: Optional[str] = None
    vintage_year: Optional[int] = None
    quantity_available: float
    price_per_tonne_eur: float
    methodology: Optional[str] = None
    co_benefits: List[str] = []
    description: Optional[str] = None
    verification_status: str
    status: str


class ListingSearchResponse(BaseModel):
    listings: List[ListingResult]
    total: int


class ListingDetailResponse(ListingResult):
    registry_project_id: Optional[str] = None
    serial_number_range: Optional[str] = None
    quantity_reserved: float = 0.0
    quantity_sold: float = 0.0
    supporting_documents: List[str] = []


class FootprintEstimateRequest(BaseModel):
    sector: str
    employees: int
    country: Optional[str] = None


class FootprintEstimateResponse(BaseModel):
    estimated_tonnes_low: float
    estimated_tonnes_high: float
    midpoint: float
    explanation: str


class OrderDraftLineItem(BaseModel):
    listing_id: str
    quantity: float


class OrderDraftRequest(BaseModel):
    buyer_id: str
    line_items: List[OrderDraftLineItem]


class OrderDraftResponse(BaseModel):
    order_id: str
    status: str
    line_items: List[dict]
    total_eur: float


class PaymentRequest(BaseModel):
    stripe_payment_intent_id: Optional[str] = None


class PaymentResponse(BaseModel):
    order_id: str
    status: str
    total_eur: float


class BuyerProfileResponse(BaseModel):
    annual_co2_tonnes_estimate: Optional[float] = None
    primary_offset_motivation: Optional[str] = None
    preferred_project_types: List[str] = []
    preferred_regions: List[str] = []
    budget_per_tonne_max_eur: Optional[float] = None
    autonomous_agent_enabled: bool = False


class MarketContextRequest(BaseModel):
    project_type: Optional[str] = None
    country: Optional[str] = None
    registry: Optional[str] = None
    category: Optional[str] = None
    limit: int = 20


class MarketContextProject(BaseModel):
    offsets_db_project_id: str
    name: Optional[str] = None
    registry: Optional[str] = None
    category: Optional[str] = None
    country: Optional[str] = None
    total_credits_issued: Optional[float] = None
    total_credits_retired: Optional[float] = None
    status: Optional[str] = None


class MarketContextResponse(BaseModel):
    projects: List[MarketContextProject]
    total: int


# ---------------------------------------------------------------------------
# Footprint estimation lookup table
# ---------------------------------------------------------------------------

# Tonnes CO2e per employee per year by sector.
# Sources: UK DEFRA, EPA, various ESG reporting benchmarks (simplified).
FOOTPRINT_PER_EMPLOYEE: Dict[str, tuple[float, float]] = {
    "technology": (2.0, 5.0),
    "software": (2.0, 5.0),
    "marketing": (2.5, 6.0),
    "consulting": (3.0, 7.0),
    "finance": (3.0, 7.0),
    "legal": (2.5, 5.5),
    "healthcare": (4.0, 8.0),
    "education": (2.0, 5.0),
    "retail": (4.0, 9.0),
    "hospitality": (5.0, 12.0),
    "manufacturing": (8.0, 20.0),
    "logistics": (10.0, 25.0),
    "transport": (10.0, 25.0),
    "construction": (8.0, 18.0),
    "agriculture": (6.0, 15.0),
    "energy": (10.0, 30.0),
    "mining": (12.0, 35.0),
    "food_beverage": (5.0, 12.0),
    "real_estate": (3.0, 7.0),
}

DEFAULT_FOOTPRINT_PER_EMPLOYEE = (3.0, 8.0)

ANALOGIES = [
    (1.0, "roughly one return economy flight from London to New York"),
    (5.0, "about the same as heating an average UK home for a year"),
    (10.0, "equivalent to driving a petrol car about 40,000 km"),
    (50.0, "comparable to the annual emissions of about 5 average European households"),
]


def _build_explanation(low: float, high: float, sector: str, employees: int) -> str:
    mid = (low + high) / 2
    analogy = ""
    for threshold, text in reversed(ANALOGIES):
        if mid >= threshold:
            analogy = f" That's {text}."
            break
    return (
        f"Based on the {sector} sector with {employees} employees, "
        f"we estimate your annual footprint is roughly {low:.0f}–{high:.0f} tonnes CO2e "
        f"(midpoint {mid:.0f} tonnes).{analogy}"
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/listings/search", response_model=ListingSearchResponse)
async def internal_search_listings(
    body: ListingSearchRequest,
    _: None = Depends(require_agent_api_key),
):
    """Search active, verified listings with agent-friendly filters."""
    results = await listing_search(
        project_type=body.project_type,
        project_country=body.project_country,
        max_price=body.max_price,
        min_quantity=body.min_quantity,
        vintage_year=body.vintage_year,
        limit=body.limit,
        offset=body.offset,
    )

    # Post-filter by co_benefits if requested
    if body.co_benefits:
        requested = set(b.lower() for b in body.co_benefits)
        results = [
            item
            for item in results
            if requested & set(b.lower() for b in item.data.co_benefits)
        ]

    listings = [
        ListingResult(
            id=item.id,
            seller_id=item.data.seller_id,
            registry_name=item.data.registry_name,
            project_name=item.data.project_name,
            project_type=item.data.project_type,
            project_country=item.data.project_country,
            vintage_year=item.data.vintage_year,
            quantity_available=item.data.quantity_tonnes
            - item.data.quantity_reserved
            - item.data.quantity_sold,
            price_per_tonne_eur=item.data.price_per_tonne_eur,
            methodology=item.data.methodology,
            co_benefits=item.data.co_benefits,
            description=item.data.description,
            verification_status=item.data.verification_status,
            status=item.data.status,
        )
        for item in results
    ]

    return ListingSearchResponse(listings=listings, total=len(listings))


@router.get("/listings/{listing_id}", response_model=ListingDetailResponse)
async def internal_get_listing(
    listing_id: str,
    _: None = Depends(require_agent_api_key),
):
    """Retrieve a single listing by ID."""
    listing = await listing_get(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    d = listing.data
    return ListingDetailResponse(
        id=listing.id,
        seller_id=d.seller_id,
        registry_name=d.registry_name,
        registry_project_id=d.registry_project_id,
        serial_number_range=d.serial_number_range,
        project_name=d.project_name,
        project_type=d.project_type,
        project_country=d.project_country,
        vintage_year=d.vintage_year,
        quantity_available=d.quantity_tonnes - d.quantity_reserved - d.quantity_sold,
        quantity_reserved=d.quantity_reserved,
        quantity_sold=d.quantity_sold,
        price_per_tonne_eur=d.price_per_tonne_eur,
        methodology=d.methodology,
        co_benefits=d.co_benefits,
        description=d.description,
        supporting_documents=d.supporting_documents,
        verification_status=d.verification_status,
        status=d.status,
    )


@router.post("/footprint/estimate", response_model=FootprintEstimateResponse)
async def internal_estimate_footprint(
    body: FootprintEstimateRequest,
    _: None = Depends(require_agent_api_key),
):
    """Estimate annual CO2 footprint from sector and headcount."""
    sector_key = body.sector.lower().replace(" ", "_").replace("-", "_")
    per_emp_low, per_emp_high = FOOTPRINT_PER_EMPLOYEE.get(
        sector_key, DEFAULT_FOOTPRINT_PER_EMPLOYEE
    )

    low = round(per_emp_low * body.employees, 1)
    high = round(per_emp_high * body.employees, 1)
    mid = round((low + high) / 2, 1)

    return FootprintEstimateResponse(
        estimated_tonnes_low=low,
        estimated_tonnes_high=high,
        midpoint=mid,
        explanation=_build_explanation(low, high, body.sector, body.employees),
    )


@router.post("/orders/draft", response_model=OrderDraftResponse)
async def internal_create_order_draft(
    body: OrderDraftRequest,
    _: None = Depends(require_agent_api_key),
):
    """Create a pending order with line items. Reserves quantity on each listing."""
    from models.operations.listings import listing_reserve_quantity

    built_items: List[OrderLineItem] = []
    total_eur = 0.0

    for item in body.line_items:
        listing = await listing_get(item.listing_id)
        if not listing:
            raise HTTPException(
                status_code=404,
                detail=f"Listing {item.listing_id} not found",
            )
        if listing.data.status != "active":
            raise HTTPException(
                status_code=400,
                detail=f"Listing {item.listing_id} is not active (status: {listing.data.status})",
            )

        available = (
            listing.data.quantity_tonnes
            - listing.data.quantity_reserved
            - listing.data.quantity_sold
        )
        if item.quantity > available:
            raise HTTPException(
                status_code=400,
                detail=f"Listing {item.listing_id}: requested {item.quantity}t but only {available}t available",
            )

        reserved = await listing_reserve_quantity(item.listing_id, item.quantity)
        if not reserved:
            raise HTTPException(
                status_code=409,
                detail=f"Could not reserve {item.quantity}t on listing {item.listing_id}",
            )

        subtotal = round(item.quantity * listing.data.price_per_tonne_eur, 2)
        total_eur += subtotal
        built_items.append(
            OrderLineItem(
                listing_id=item.listing_id,
                quantity=item.quantity,
                price_per_tonne=listing.data.price_per_tonne_eur,
                subtotal=subtotal,
            )
        )

    total_eur = round(total_eur, 2)
    order = await order_create(body.buyer_id, built_items, total_eur)

    return OrderDraftResponse(
        order_id=order.id,
        status=order.data.status,
        line_items=[li.model_dump() for li in order.data.line_items],
        total_eur=order.data.total_eur,
    )


@router.post("/orders/{order_id}/pay", response_model=PaymentResponse)
async def internal_execute_payment(
    order_id: str,
    body: PaymentRequest,
    _: None = Depends(require_agent_api_key),
):
    """
    Execute payment for an order (used by autonomous agent).
    In the hackathon build this records the intent and marks the order confirmed;
    actual Stripe Agent Wallet charging is a future integration.
    """
    order = await order_get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.data.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Order is not pending (status: {order.data.status})",
        )

    if body.stripe_payment_intent_id:
        await order_set_payment_intent(order_id, body.stripe_payment_intent_id)

    await order_update_payment_status(order_id, "succeeded")
    updated = await order_update_status(order_id, "completed")
    await order_record_ledger_entries(order_id)

    # Move reserved → sold on each listing
    for li in order.data.line_items:
        listing = await listing_get(li.listing_id)
        if listing:
            listing.data.quantity_reserved -= li.quantity
            listing.data.quantity_sold += li.quantity
            if listing.data.quantity_sold >= listing.data.quantity_tonnes:
                listing.data.status = "sold_out"
            await listing_update(listing)

    logger.info(f"Order {order_id} completed via internal pay")

    return PaymentResponse(
        order_id=order_id,
        status=updated.data.status,
        total_eur=updated.data.total_eur,
    )


@router.get("/buyers/{buyer_id}/profile", response_model=BuyerProfileResponse)
async def internal_get_buyer_profile(
    buyer_id: str,
    _: None = Depends(require_agent_api_key),
):
    """Read buyer profile sub-document from User document."""
    try:
        profile = await user_get_buyer_profile(buyer_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Buyer not found")

    if not profile:
        return BuyerProfileResponse()

    return BuyerProfileResponse(
        annual_co2_tonnes_estimate=profile.annual_co2_tonnes_estimate,
        primary_offset_motivation=profile.primary_offset_motivation,
        preferred_project_types=profile.preferred_project_types,
        preferred_regions=profile.preferred_regions,
        budget_per_tonne_max_eur=profile.budget_per_tonne_max_eur,
        autonomous_agent_enabled=profile.autonomous_agent_enabled,
    )


@router.post("/offsets-db/market-context", response_model=MarketContextResponse)
async def internal_get_market_context(
    body: MarketContextRequest,
    _: None = Depends(require_agent_api_key),
):
    """
    Query OffsetsDB project documents cached in Couchbase for market context.
    Used by the seller advisory agent and autonomous buyer agent.
    """
    from models.entities.couchbase.offsets_db_projects import OffsetsDBProject

    keyspace = OffsetsDBProject.get_keyspace()
    conditions = ["1=1"]
    params: Dict[str, str] = {}

    if body.project_type:
        conditions.append("project_type = $project_type")
        params["project_type"] = body.project_type
    if body.country:
        conditions.append("country = $country")
        params["country"] = body.country
    if body.registry:
        conditions.append("registry = $registry")
        params["registry"] = body.registry
    if body.category:
        conditions.append("category = $category")
        params["category"] = body.category

    where = " AND ".join(conditions)
    collection_name = OffsetsDBProject._collection_name
    query = (
        f"SELECT META().id, * FROM {keyspace} "
        f"WHERE {where} "
        f"ORDER BY total_credits_issued DESC "
        f"LIMIT {body.limit}"
    )

    try:
        rows = await keyspace.query(query, **params)
    except Exception as e:
        logger.warning(f"OffsetsDB market context query failed: {e}")
        return MarketContextResponse(projects=[], total=0)

    projects = []
    for row in rows:
        data = row.get(collection_name, row)
        if isinstance(data, dict):
            projects.append(
                MarketContextProject(
                    offsets_db_project_id=data.get(
                        "offsets_db_project_id", row.get("id", "")
                    ),
                    name=data.get("name"),
                    registry=data.get("registry"),
                    category=data.get("category"),
                    country=data.get("country"),
                    total_credits_issued=data.get("total_credits_issued"),
                    total_credits_retired=data.get("total_credits_retired"),
                    status=data.get("status"),
                )
            )

    return MarketContextResponse(projects=projects, total=len(projects))
