from typing import Any, Dict, List, Optional
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


async def listing_reserve_quantity(listing_id: str, quantity: float) -> bool:
    """Reserve (or release) quantity on a listing via read-modify-write.

    Pass a negative *quantity* to release a previous reservation.
    Not fully atomic under concurrency — acceptable for hackathon;
    production would need a CAS-guarded loop.
    """
    try:
        listing = await Listing.get(listing_id)
        if not listing:
            return False
        new_reserved = listing.data.quantity_reserved + quantity
        # When releasing (negative qty), don't let reserved go below 0
        if quantity < 0:
            new_reserved = max(new_reserved, 0.0)
        # When reserving, check we don't exceed available
        available = listing.data.quantity_tonnes - listing.data.quantity_sold
        if new_reserved > available:
            return False
        listing.data.quantity_reserved = new_reserved
        await Listing.update(listing)
        return True
    except Exception:
        return False


async def listing_release_reservation(listing_id: str, quantity: float) -> bool:
    """Release reserved quantity on a listing."""
    try:
        listing = await Listing.get(listing_id)
        if not listing:
            return False
        listing.data.quantity_reserved = max(listing.data.quantity_reserved - quantity, 0.0)
        await Listing.update(listing)
        return True
    except Exception:
        return False


async def listing_confirm_sale(listing_id: str, quantity: float) -> bool:
    """Move quantity from reserved to sold."""
    try:
        listing = await Listing.get(listing_id)
        if not listing:
            return False
        listing.data.quantity_reserved = max(listing.data.quantity_reserved - quantity, 0.0)
        listing.data.quantity_sold += quantity
        if listing.data.quantity_sold >= listing.data.quantity_tonnes:
            listing.data.status = "sold_out"
        await Listing.update(listing)
        return True
    except Exception:
        return False
