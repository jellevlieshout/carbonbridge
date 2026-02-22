import asyncio
from typing import Any, Callable, Dict, List, Optional

from couchbase.exceptions import CASMismatchException

from models.entities.couchbase.listings import Listing, ListingData


async def listing_create(seller_id: str, data: ListingData) -> Listing:
    data.seller_id = seller_id
    return await Listing.create(data, user_id=seller_id)


async def listing_get(listing_id: str) -> Optional[Listing]:
    return await Listing.get(listing_id)


async def listing_update(listing: Listing) -> Listing:
    return await Listing.update(listing)


async def listing_soft_delete(listing_id: str) -> Optional[Listing]:
    listing = await Listing.get(listing_id)
    if not listing:
        return None
    listing.data.status = "paused"
    return await Listing.update(listing)


async def listing_search(
    project_type: Optional[str] = None,
    project_country: Optional[str] = None,
    max_price: Optional[float] = None,
    min_quantity: Optional[float] = None,
    vintage_year: Optional[int] = None,
    status: str = "active",
    limit: int = 50,
    offset: int = 0,
) -> List[Listing]:
    keyspace = Listing.get_keyspace()
    conditions = ["status = $status", "verification_status = 'verified'"]
    params: Dict[str, Any] = {"status": status}

    if project_type:
        conditions.append("project_type = $project_type")
        params["project_type"] = project_type
    if project_country:
        conditions.append("project_country = $project_country")
        params["project_country"] = project_country
    if max_price is not None:
        conditions.append("price_per_tonne_eur <= $max_price")
        params["max_price"] = max_price
    if min_quantity is not None:
        conditions.append("(quantity_tonnes - quantity_reserved - quantity_sold) >= $min_quantity")
        params["min_quantity"] = min_quantity
    if vintage_year is not None:
        conditions.append("vintage_year = $vintage_year")
        params["vintage_year"] = vintage_year

    where = " AND ".join(conditions)
    query = (
        f"SELECT META().id, * FROM {keyspace} "
        f"WHERE {where} "
        f"ORDER BY created_at DESC "
        f"LIMIT {limit} OFFSET {offset}"
    )
    rows = await keyspace.query(query, **params)
    return [
        Listing(id=row["id"], data=row.get("listings"))
        for row in rows if row.get("listings")
    ]


async def listing_get_by_seller(seller_id: str) -> List[Listing]:
    keyspace = Listing.get_keyspace()
    query = (
        f"SELECT META().id, * FROM {keyspace} "
        f"WHERE seller_id = $seller_id ORDER BY created_at DESC"
    )
    rows = await keyspace.query(query, seller_id=seller_id)
    return [
        Listing(id=row["id"], data=row.get("listings"))
        for row in rows if row.get("listings")
    ]


async def _listing_cas_retry(
    listing_id: str,
    mutator: Callable[[ListingData], Optional[str]],
    max_retries: int = 5,
) -> tuple[bool, Optional[str]]:
    """Read-modify-write a listing with CAS-guarded retry.

    *mutator* receives ``ListingData`` and mutates it in place.  It returns
    ``None`` on success or an error string to abort early (e.g. "insufficient
    availability").  On ``CASMismatchException`` the helper re-reads and
    retries with exponential backoff (10 ms, 20 ms, 40 ms, …).
    """
    backoff_ms = 10
    for attempt in range(max_retries + 1):
        listing = await Listing.get(listing_id)
        if not listing:
            return False, f"Listing {listing_id} not found"

        error = mutator(listing.data)
        if error is not None:
            return False, error

        try:
            await Listing.update(listing)
            return True, None
        except CASMismatchException:
            if attempt == max_retries:
                return False, "Concurrent update conflict — please retry"
            await asyncio.sleep(backoff_ms / 1000)
            backoff_ms *= 2

    return False, "Max retries exceeded"


async def listing_reserve_quantity(
    listing_id: str, quantity: float
) -> tuple[bool, Optional[str]]:
    """Atomically reserve quantity on a listing (CAS-guarded)."""

    def _mutate(data: ListingData) -> Optional[str]:
        new_reserved = data.quantity_reserved + quantity
        if quantity < 0:
            new_reserved = max(new_reserved, 0.0)
        available = data.quantity_tonnes - data.quantity_sold
        if new_reserved > available:
            avail_for_reserve = available - data.quantity_reserved
            return (
                f"Insufficient availability: requested {quantity}t "
                f"but only {avail_for_reserve}t available"
            )
        data.quantity_reserved = new_reserved
        return None

    return await _listing_cas_retry(listing_id, _mutate)


async def listing_release_reservation(
    listing_id: str, quantity: float
) -> tuple[bool, Optional[str]]:
    """Atomically release reserved quantity on a listing (CAS-guarded)."""

    def _mutate(data: ListingData) -> Optional[str]:
        data.quantity_reserved = max(data.quantity_reserved - quantity, 0.0)
        return None

    return await _listing_cas_retry(listing_id, _mutate)


async def listing_confirm_sale(
    listing_id: str, quantity: float
) -> tuple[bool, Optional[str]]:
    """Atomically move quantity from reserved to sold (CAS-guarded)."""

    def _mutate(data: ListingData) -> Optional[str]:
        data.quantity_reserved = max(data.quantity_reserved - quantity, 0.0)
        data.quantity_sold += quantity
        if data.quantity_sold >= data.quantity_tonnes:
            data.status = "sold_out"
        return None

    return await _listing_cas_retry(listing_id, _mutate)
