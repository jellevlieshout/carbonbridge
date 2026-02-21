from typing import List, Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from models.entities.couchbase.listings import ListingData
from models.operations.listings import (
    listing_create,
    listing_get,
    listing_search,
    listing_soft_delete,
    listing_update,
)
from models.operations.registry_verifications import verification_create
from utils import log
from .dependencies import require_authenticated
from .fake_registry import get_project, get_credits

logger = log.get_logger(__name__)

router = APIRouter(prefix="/listings", tags=["listings"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ListingCreateRequest(BaseModel):
    registry_name: str
    registry_project_id: Optional[str] = None
    serial_number_range: Optional[str] = None
    project_name: str
    project_type: Literal[
        "afforestation", "renewable", "cookstoves", "methane_capture",
        "fuel_switching", "energy_efficiency", "agriculture", "other"
    ] = "other"
    project_country: Optional[str] = None
    vintage_year: Optional[int] = None
    quantity_tonnes: float
    price_per_tonne_eur: float
    methodology: Optional[str] = None
    co_benefits: List[str] = []
    description: Optional[str] = None
    supporting_documents: List[str] = []


class ListingUpdateRequest(BaseModel):
    registry_name: Optional[str] = None
    registry_project_id: Optional[str] = None
    serial_number_range: Optional[str] = None
    project_name: Optional[str] = None
    project_type: Optional[Literal[
        "afforestation", "renewable", "cookstoves", "methane_capture",
        "fuel_switching", "energy_efficiency", "agriculture", "other"
    ]] = None
    project_country: Optional[str] = None
    vintage_year: Optional[int] = None
    quantity_tonnes: Optional[float] = None
    price_per_tonne_eur: Optional[float] = None
    methodology: Optional[str] = None
    co_benefits: Optional[List[str]] = None
    description: Optional[str] = None
    supporting_documents: Optional[List[str]] = None
    status: Optional[Literal["draft", "active", "paused", "sold_out"]] = None


class ListingResponse(BaseModel):
    id: str
    seller_id: str
    registry_name: str
    registry_project_id: Optional[str] = None
    serial_number_range: Optional[str] = None
    project_name: str
    project_type: str
    project_country: Optional[str] = None
    vintage_year: Optional[int] = None
    quantity_tonnes: float
    quantity_reserved: float
    quantity_sold: float
    price_per_tonne_eur: float
    verification_status: str
    methodology: Optional[str] = None
    co_benefits: List[str] = []
    description: Optional[str] = None
    supporting_documents: List[str] = []
    status: str


class ListingSearchResponse(BaseModel):
    listings: List[ListingResponse]
    count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _listing_to_response(listing) -> ListingResponse:
    return ListingResponse(id=listing.id, **listing.data.model_dump())


def _verify_ownership(listing, user_id: str):
    if listing.data.seller_id != user_id:
        raise HTTPException(status_code=403, detail="You do not own this listing")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/", response_model=ListingSearchResponse)
async def route_listing_search(
    project_type: Optional[str] = Query(None),
    project_country: Optional[str] = Query(None),
    max_price: Optional[float] = Query(None),
    min_quantity: Optional[float] = Query(None),
    vintage_year: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Public search across active, verified listings."""
    results = await listing_search(
        project_type=project_type,
        project_country=project_country,
        max_price=max_price,
        min_quantity=min_quantity,
        vintage_year=vintage_year,
        limit=limit,
        offset=offset,
    )
    return ListingSearchResponse(
        listings=[_listing_to_response(item) for item in results],
        count=len(results),
    )


@router.get("/{listing_id}", response_model=ListingResponse)
async def route_listing_get(listing_id: str):
    """Get a single listing by ID (public)."""
    listing = await listing_get(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return _listing_to_response(listing)


@router.post("/", response_model=ListingResponse, status_code=201)
async def route_listing_create(
    body: ListingCreateRequest,
    user: dict = Depends(require_authenticated),
):
    """Create a new listing (seller only)."""
    seller_id = user["sub"]
    data = ListingData(seller_id=seller_id, **body.model_dump())
    listing = await listing_create(seller_id, data)
    return _listing_to_response(listing)


@router.put("/{listing_id}", response_model=ListingResponse)
async def route_listing_update(
    listing_id: str,
    body: ListingUpdateRequest,
    user: dict = Depends(require_authenticated),
):
    """Update a listing (seller-owner only). Partial update — only provided fields are changed."""
    listing = await listing_get(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    _verify_ownership(listing, user["sub"])

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(listing.data, field, value)

    updated = await listing_update(listing)
    return _listing_to_response(updated)


@router.delete("/{listing_id}", status_code=204)
async def route_listing_delete(
    listing_id: str,
    user: dict = Depends(require_authenticated),
):
    """Soft-delete a listing by setting status to 'paused' (seller-owner only)."""
    listing = await listing_get(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    _verify_ownership(listing, user["sub"])

    await listing_soft_delete(listing_id)


@router.post("/{listing_id}/verify", response_model=ListingResponse)
async def route_listing_verify(
    listing_id: str,
    user: dict = Depends(require_authenticated),
):
    """
    Verify a listing against the fake registry (seller-owner only).
    Calls the fake registry project + credits endpoints, stores a
    RegistryVerification document, and updates the listing's verification_status.
    """
    listing = await listing_get(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    _verify_ownership(listing, user["sub"])

    project_id = listing.data.registry_project_id
    serial_range = listing.data.serial_number_range

    if not project_id:
        raise HTTPException(status_code=400, detail="Listing has no registry_project_id")

    raw_response: dict = {}
    project_verified = False
    serial_numbers_available = False
    error_message = None

    # 1. Verify project exists in registry
    try:
        project_meta = await get_project(project_id)
        raw_response["project"] = project_meta.model_dump()
        project_verified = project_meta.status == "active"
    except HTTPException as e:
        error_message = f"Registry project lookup failed: {e.detail}"
    except Exception as e:
        error_message = f"Registry project lookup error: {str(e)}"

    # 2. Verify credit serial numbers if provided
    if serial_range and not error_message:
        try:
            credit_info = await get_credits(serial_range)
            raw_response["credits"] = credit_info.model_dump()
            serial_numbers_available = credit_info.is_valid and credit_info.available_quantity > 0
        except HTTPException as e:
            error_message = f"Registry credits lookup failed: {e.detail}"
        except Exception as e:
            error_message = f"Registry credits lookup error: {str(e)}"

    is_valid = project_verified and (serial_numbers_available if serial_range else True) and not error_message

    # 3. Store verification record
    await verification_create(
        listing_id=listing_id,
        raw_response=raw_response,
        is_valid=is_valid,
        project_verified=project_verified,
        serial_numbers_available=serial_numbers_available,
        error_message=error_message,
    )

    # 4. Update listing verification status
    listing.data.verification_status = "verified" if is_valid else "failed"
    updated = await listing_update(listing)
    return _listing_to_response(updated)
