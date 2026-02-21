from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from models.entities.couchbase.listings import ListingData
from models.operations.listings import (
    listing_create,
    listing_get,
    listing_get_by_seller,
    listing_soft_delete,
    listing_update,
)
from models.operations.registry_verifications import (
    verification_create,
    verification_get_latest_for_listing,
)
from utils import log

from .dependencies import require_seller

logger = log.get_logger(__name__)

router = APIRouter(tags=["listings"])


# ── Request models ────────────────────────────────────────────────────────────

class ListingCreateRequest(BaseModel):
    registry_name: str
    registry_project_id: Optional[str] = None
    serial_number_range: Optional[str] = None
    project_name: str
    project_type: str = "other"
    project_country: Optional[str] = None
    vintage_year: Optional[int] = None
    quantity_tonnes: float
    price_per_tonne_eur: float
    methodology: Optional[str] = None
    co_benefits: List[str] = []
    description: Optional[str] = None
    supporting_documents: List[str] = []
    status: str = "draft"


class ListingUpdateRequest(BaseModel):
    registry_name: Optional[str] = None
    registry_project_id: Optional[str] = None
    serial_number_range: Optional[str] = None
    project_name: Optional[str] = None
    project_type: Optional[str] = None
    project_country: Optional[str] = None
    vintage_year: Optional[int] = None
    quantity_tonnes: Optional[float] = None
    price_per_tonne_eur: Optional[float] = None
    methodology: Optional[str] = None
    co_benefits: Optional[List[str]] = None
    description: Optional[str] = None
    supporting_documents: Optional[List[str]] = None
    status: Optional[str] = None


class VerificationResult(BaseModel):
    listing_id: str
    verification_id: str
    is_valid: bool
    project_verified: bool
    serial_numbers_available: bool
    verification_status: str
    project_data: Optional[Dict[str, Any]] = None
    credits_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    queried_at: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _seller_id(user: dict) -> str:
    uid = user.get("sub")
    if not uid:
        raise HTTPException(status_code=400, detail="User ID not found in token")
    return uid


def _assert_owns_listing(listing, seller_id: str) -> None:
    if listing.data.seller_id != seller_id:
        raise HTTPException(status_code=403, detail="Not your listing")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/listings", status_code=201)
async def route_listing_create(
    body: ListingCreateRequest,
    user: dict = Depends(require_seller),
) -> Dict[str, Any]:
    seller_id = _seller_id(user)
    data = ListingData(seller_id=seller_id, **body.model_dump())
    listing = await listing_create(seller_id, data)
    return {"id": listing.id, **listing.data.model_dump()}


@router.get("/listings")
async def route_listing_list(
    user: dict = Depends(require_seller),
) -> List[Dict[str, Any]]:
    seller_id = _seller_id(user)
    listings = await listing_get_by_seller(seller_id)
    return [{"id": listing.id, **listing.data.model_dump()} for listing in listings]


@router.get("/listings/{listing_id}")
async def route_listing_get(
    listing_id: str,
    user: dict = Depends(require_seller),
) -> Dict[str, Any]:
    listing = await listing_get(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    _assert_owns_listing(listing, _seller_id(user))

    result: Dict[str, Any] = {"id": listing.id, **listing.data.model_dump()}

    latest = await verification_get_latest_for_listing(listing_id)
    if latest:
        result["latest_verification"] = {"id": latest.id, **latest.data.model_dump()}

    return result


@router.put("/listings/{listing_id}")
async def route_listing_update(
    listing_id: str,
    body: ListingUpdateRequest,
    user: dict = Depends(require_seller),
) -> Dict[str, Any]:
    listing = await listing_get(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    _assert_owns_listing(listing, _seller_id(user))

    _REGISTRY_FIELDS = {"registry_name", "registry_project_id", "serial_number_range"}
    registry_changed = False

    for field, value in body.model_dump(exclude_none=True).items():
        if field in _REGISTRY_FIELDS and getattr(listing.data, field) != value:
            registry_changed = True
        setattr(listing.data, field, value)

    # Editing registry details resets verification so the seller must re-verify
    if registry_changed:
        listing.data.verification_status = "pending"

    updated = await listing_update(listing)
    return {
        "id": updated.id,
        **updated.data.model_dump(),
        "re_verification_required": registry_changed,
    }


@router.delete("/listings/{listing_id}", status_code=204)
async def route_listing_delete(
    listing_id: str,
    user: dict = Depends(require_seller),
) -> None:
    listing = await listing_get(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    _assert_owns_listing(listing, _seller_id(user))
    await listing_soft_delete(listing_id)


@router.post("/listings/{listing_id}/verify", response_model=VerificationResult)
async def route_listing_verify(
    listing_id: str,
    user: dict = Depends(require_seller),
) -> VerificationResult:
    """
    Trigger registry verification for a listing.

    Calls the Fake Registry for both project metadata and serial-number credits,
    persists a RegistryVerification document, and updates listing.verification_status
    to 'verified' or 'failed'. Returns the full result inline so the frontend can
    show a green badge or a rejection reason without a follow-up request.
    """
    listing = await listing_get(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    _assert_owns_listing(listing, _seller_id(user))

    # Import here to avoid circular import at module load time
    from routes.fake_registry import get_credits, get_project

    project_data: Optional[Dict[str, Any]] = None
    credits_data: Optional[Dict[str, Any]] = None
    errors: List[str] = []
    project_verified = False
    serial_numbers_available = False

    # ── 1. Project lookup ─────────────────────────────────────────────────────
    if listing.data.registry_project_id:
        try:
            meta = await get_project(listing.data.registry_project_id)
            project_data = meta.model_dump()
            project_verified = meta.status == "active"
            if not project_verified:
                errors.append(
                    f"Project status is '{meta.status}', expected 'active'"
                )
        except HTTPException as exc:
            if exc.status_code == 503:
                errors.append("Registry temporarily unavailable (project lookup)")
            elif exc.status_code == 404:
                errors.append(
                    f"Project '{listing.data.registry_project_id}' not found in registry"
                )
            else:
                detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
                errors.append(f"Registry error during project lookup: {detail}")
    else:
        errors.append("Listing has no registry_project_id")

    # ── 2. Serial-number / credits lookup ─────────────────────────────────────
    if listing.data.serial_number_range:
        try:
            credit_val = await get_credits(listing.data.serial_number_range)
            credits_data = credit_val.model_dump()
            serial_numbers_available = (
                credit_val.is_valid
                and credit_val.available_quantity > 0
                and credit_val.retirement_status != "retired"
            )
            if not credit_val.is_valid:
                errors.append("Serial number range not recognised by registry")
            elif credit_val.retirement_status == "retired":
                errors.append("All credits in this serial range are already retired")
            elif credit_val.available_quantity <= 0:
                errors.append("No available credits remaining for this serial range")
        except HTTPException as exc:
            if exc.status_code == 503:
                errors.append("Registry temporarily unavailable (credits lookup)")
            else:
                detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
                errors.append(f"Registry error during credits lookup: {detail}")
    else:
        errors.append("Listing has no serial_number_range")

    # ── 3. Persist result & update listing ────────────────────────────────────
    is_valid = project_verified and serial_numbers_available
    error_message = "; ".join(errors) if errors else None

    verification = await verification_create(
        listing_id=listing_id,
        raw_response={"project": project_data, "credits": credits_data},
        is_valid=is_valid,
        serial_numbers_available=serial_numbers_available,
        project_verified=project_verified,
        error_message=error_message,
    )

    listing.data.verification_status = "verified" if is_valid else "failed"
    await listing_update(listing)

    queried_at = (
        verification.data.queried_at.isoformat()
        if verification.data.queried_at
        else datetime.now(timezone.utc).isoformat()
    )

    return VerificationResult(
        listing_id=listing_id,
        verification_id=verification.id,
        is_valid=is_valid,
        project_verified=project_verified,
        serial_numbers_available=serial_numbers_available,
        verification_status=listing.data.verification_status,
        project_data=project_data,
        credits_data=credits_data,
        error_message=error_message,
        queried_at=queried_at,
    )
