"""
Auction business logic with CAS-guarded atomic operations.

Follows the same patterns as operations/listings.py:
- _auction_cas_retry for atomic read-modify-write
- Exponential backoff on CASMismatchException
- listing_reserve_quantity / listing_release_reservation for inventory
"""

import asyncio
import hashlib
import logging
from typing import Any, Callable, Dict, List, Optional, Literal
from datetime import datetime, timezone, timedelta

from couchbase.exceptions import CASMismatchException

from models.entities.couchbase.auctions import Auction, AuctionData, AuctionConfig
from models.entities.couchbase.bids import Bid, BidData
from models.entities.couchbase.orders import OrderLineItem
from models.operations.listings import (
    listing_get,
    listing_reserve_quantity,
    listing_release_reservation,
    listing_confirm_sale,
)
from models.operations.orders import (
    order_create,
    order_set_payment_intent,
    order_set_payment_link,
    order_update_status,
    order_record_ledger_entries,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CAS-retry helper (same pattern as listings.py)
# ---------------------------------------------------------------------------

async def _auction_cas_retry(
    auction_id: str,
    mutator: Callable[[AuctionData], Optional[str]],
    max_retries: int = 5,
) -> tuple[bool, Optional[str]]:
    """Read-modify-write an auction with CAS-guarded retry.

    *mutator* receives ``AuctionData`` and mutates it in place.  It returns
    ``None`` on success or an error string to abort early.  On
    ``CASMismatchException`` the helper re-reads and retries with
    exponential backoff (10 ms, 20 ms, 40 ms, …).
    """
    backoff_ms = 10
    for attempt in range(max_retries + 1):
        auction = await Auction.get(auction_id)
        if not auction:
            return False, f"Auction {auction_id} not found"

        error = mutator(auction.data)
        if error is not None:
            return False, error

        try:
            await Auction.update(auction)
            return True, None
        except CASMismatchException:
            if attempt == max_retries:
                return False, "Concurrent update conflict — please retry"
            await asyncio.sleep(backoff_ms / 1000)
            backoff_ms *= 2

    return False, "Max retries exceeded"


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

async def auction_create(
    seller_id: str,
    listing_id: str,
    config: AuctionConfig,
    quantity_tonnes: float,
    starts_at: datetime,
    ends_at: datetime,
    created_by: Literal["human", "agent"] = "human",
    agent_run_id: Optional[str] = None,
) -> Auction:
    """Create an auction and reserve the quantity on the underlying listing."""
    listing = await listing_get(listing_id)
    if not listing:
        raise ValueError(f"Listing {listing_id} not found")
    if listing.data.seller_id != seller_id:
        raise ValueError("Listing does not belong to seller")
    if listing.data.status != "active":
        raise ValueError(f"Listing is not active (status: {listing.data.status})")

    # Reserve inventory on the listing via existing CAS mechanism
    reserved, err = await listing_reserve_quantity(listing_id, quantity_tonnes)
    if not reserved:
        raise ValueError(f"Cannot reserve quantity: {err}")

    now = datetime.now(timezone.utc)
    data = AuctionData(
        seller_id=seller_id,
        listing_id=listing_id,
        created_by=created_by,
        agent_run_id=agent_run_id,
        config=config,
        quantity_tonnes=quantity_tonnes,
        starts_at=starts_at,
        ends_at=ends_at,
        effective_ends_at=ends_at,
        status="scheduled" if starts_at > now else "active",
    )
    return await Auction.create(data, user_id=seller_id)


async def auction_get(auction_id: str) -> Optional[Auction]:
    return await Auction.get(auction_id)


async def auction_search(
    status: Optional[str] = "active",
    project_type: Optional[str] = None,
    max_current_bid: Optional[float] = None,
    seller_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Auction]:
    """Search auctions with optional filters."""
    keyspace = Auction.get_keyspace()
    conditions = []
    params: Dict[str, Any] = {}

    if status:
        conditions.append("status = $status")
        params["status"] = status
    if seller_id:
        conditions.append("seller_id = $seller_id")
        params["seller_id"] = seller_id
    if max_current_bid is not None:
        conditions.append(
            "(current_high_bid_eur IS NULL OR current_high_bid_eur <= $max_bid)"
        )
        params["max_bid"] = max_current_bid

    where = " AND ".join(conditions) if conditions else "1=1"
    query = (
        f"SELECT META().id, * FROM {keyspace} "
        f"WHERE {where} "
        f"ORDER BY created_at DESC "
        f"LIMIT {limit} OFFSET {offset}"
    )
    rows = await keyspace.query(query, **params)
    return [
        Auction(id=row["id"], data=row.get("auctions"))
        for row in rows if row.get("auctions")
    ]


async def auction_get_by_seller(seller_id: str) -> List[Auction]:
    keyspace = Auction.get_keyspace()
    query = (
        f"SELECT META().id, * FROM {keyspace} "
        f"WHERE seller_id = $seller_id ORDER BY created_at DESC"
    )
    rows = await keyspace.query(query, seller_id=seller_id)
    return [
        Auction(id=row["id"], data=row.get("auctions"))
        for row in rows if row.get("auctions")
    ]


# ---------------------------------------------------------------------------
# Bid placement (CAS-critical)
# ---------------------------------------------------------------------------

async def auction_place_bid(
    auction_id: str,
    bidder_id: str,
    amount_per_tonne_eur: float,
    placed_by: Literal["human", "agent"] = "human",
    agent_run_id: Optional[str] = None,
) -> tuple[Optional[Bid], Optional[str]]:
    """
    Atomically place a bid on an auction.

    CAS flow:
    1. Read auction with CAS
    2. Validate (status, timing, amount, not own auction)
    3. Create Bid document
    4. CAS-update auction's denormalized high-bid fields
    5. If anti-snipe window hit, extend effective_ends_at
    6. If buy-now triggered, set status to bought_now
    7. Mark previous high bid as outbid

    Returns (bid, error_string). On success error is None.
    """
    auction = await Auction.get(auction_id)
    if not auction:
        return None, "Auction not found"

    data = auction.data
    now = datetime.now(timezone.utc)

    # Validate auction state
    if data.status != "active":
        return None, f"Auction is not active (status: {data.status})"
    if now > data.effective_ends_at:
        return None, "Auction has ended"
    if data.seller_id == bidder_id:
        return None, "Sellers cannot bid on their own auction"

    # Validate bid amount
    min_bid = data.config.starting_price_per_tonne_eur
    if data.current_high_bid_eur is not None:
        min_bid = data.current_high_bid_eur + data.config.min_bid_increment_eur
    if amount_per_tonne_eur < min_bid:
        return None, f"Bid must be at least EUR {min_bid:.2f}/t"

    # Check buy-now price
    is_buy_now = False
    if (
        data.config.buy_now_price_per_tonne_eur
        and amount_per_tonne_eur >= data.config.buy_now_price_per_tonne_eur
    ):
        is_buy_now = True
        amount_per_tonne_eur = data.config.buy_now_price_per_tonne_eur

    total = round(amount_per_tonne_eur * data.quantity_tonnes, 2)

    # Create bid document
    bid_data = BidData(
        auction_id=auction_id,
        bidder_id=bidder_id,
        amount_per_tonne_eur=amount_per_tonne_eur,
        total_eur=total,
        placed_at=now,
        placed_by=placed_by,
        agent_run_id=agent_run_id,
        status="buy_now" if is_buy_now else "active",
        is_buy_now=is_buy_now,
    )
    bid = await Bid.create(bid_data, user_id=bidder_id)

    # Remember previous high bidder for outbid notification
    previous_high_bid_id = data.current_high_bid_id

    # CAS-update auction with new high bid
    def _mutate(d: AuctionData) -> Optional[str]:
        # Re-validate after re-read (CAS retry may re-read a newer doc)
        if d.status != "active":
            return f"Auction is no longer active (status: {d.status})"

        d.current_high_bid_eur = amount_per_tonne_eur
        d.current_high_bid_id = bid.id
        d.current_high_bidder_id = bidder_id
        d.bid_count += 1

        # Anti-snipe extension
        time_remaining = d.effective_ends_at - now
        if time_remaining.total_seconds() <= d.config.auto_extend_minutes * 60:
            d.effective_ends_at += timedelta(
                minutes=d.config.auto_extend_duration_minutes
            )
            d.extensions_count += 1

        # Buy-now triggers immediate settlement
        if is_buy_now:
            d.status = "bought_now"
            d.winner_id = bidder_id
            d.winning_bid_id = bid.id
            d.winning_price_per_tonne_eur = amount_per_tonne_eur

        return None

    ok, err = await _auction_cas_retry(auction_id, _mutate)
    if not ok:
        return None, err

    # Mark previous high bid as outbid
    if previous_high_bid_id and not is_buy_now:
        try:
            prev_bid = await Bid.get(previous_high_bid_id)
            if prev_bid and prev_bid.data.status == "active":
                prev_bid.data.status = "outbid"
                await Bid.update(prev_bid)
        except Exception as e:
            logger.warning(f"Failed to mark bid {previous_high_bid_id} as outbid: {e}")

    return bid, None


# ---------------------------------------------------------------------------
# Lifecycle transitions
# ---------------------------------------------------------------------------

async def auction_activate(auction_id: str) -> tuple[bool, Optional[str]]:
    """Transition a scheduled auction to active (called by scheduler)."""

    def _mutate(d: AuctionData) -> Optional[str]:
        if d.status != "scheduled":
            return f"Cannot activate: status is {d.status}"
        d.status = "active"
        return None

    return await _auction_cas_retry(auction_id, _mutate)


async def auction_cancel(auction_id: str) -> tuple[bool, Optional[str]]:
    """Cancel an auction. Only allowed if no bids have been placed."""
    auction = await Auction.get(auction_id)
    if not auction:
        return False, "Auction not found"
    if auction.data.bid_count > 0:
        return False, "Cannot cancel auction with existing bids"
    if auction.data.status not in ("scheduled", "active"):
        return False, f"Cannot cancel auction with status: {auction.data.status}"

    # Release reserved inventory
    ok, err = await listing_release_reservation(
        auction.data.listing_id, auction.data.quantity_tonnes
    )
    if not ok:
        logger.warning(f"Failed to release reservation on cancel: {err}")

    def _mutate(d: AuctionData) -> Optional[str]:
        d.status = "cancelled"
        return None

    return await _auction_cas_retry(auction_id, _mutate)


async def auction_fail(
    auction_id: str, reason: str = "No bids received"
) -> tuple[bool, Optional[str]]:
    """Mark auction as failed and release inventory."""
    auction = await Auction.get(auction_id)
    if not auction:
        return False, "Auction not found"

    # Release reserved inventory back to listing
    ok, err = await listing_release_reservation(
        auction.data.listing_id, auction.data.quantity_tonnes
    )
    if not ok:
        logger.warning(f"Failed to release reservation on auction fail: {err}")

    def _mutate(d: AuctionData) -> Optional[str]:
        d.status = "failed"
        return None

    ok, err = await _auction_cas_retry(auction_id, _mutate)
    if ok:
        logger.info(f"Auction {auction_id} failed: {reason}")
    return ok, err


# ---------------------------------------------------------------------------
# Settlement
# ---------------------------------------------------------------------------

async def auction_settle(auction_id: str) -> tuple[bool, Optional[str]]:
    """
    Called by the scheduler when an auction's effective_ends_at has passed.
    Determines winner, creates order, initiates payment.

    Reuses the existing order + Stripe + TigerBeetle pipeline.
    """
    auction = await Auction.get(auction_id)
    if not auction:
        return False, "Auction not found"
    if auction.data.status not in ("active", "ended", "bought_now"):
        return False, f"Auction not in settleable state (status: {auction.data.status})"

    d = auction.data

    # Mark as ended first (if still active)
    if d.status == "active":
        def _mark_ended(ad: AuctionData) -> Optional[str]:
            ad.status = "ended"
            return None
        await _auction_cas_retry(auction_id, _mark_ended)

    # Check if reserve price was met
    if d.config.reserve_price_per_tonne_eur:
        if (d.current_high_bid_eur or 0) < d.config.reserve_price_per_tonne_eur:
            return await auction_fail(auction_id, "Reserve price not met")

    # No bids case
    if d.bid_count == 0 or not d.current_high_bid_id:
        return await auction_fail(auction_id, "No bids received")

    # We have a winner
    winning_bid = await Bid.get(d.current_high_bid_id)
    if not winning_bid:
        return False, "Winning bid document not found"

    # Mark winning bid
    winning_bid.data.status = "won"
    await Bid.update(winning_bid)

    # Mark all other bids as lost
    all_bids = await auction_get_bids(auction_id)
    for b in all_bids:
        if b.id != winning_bid.id and b.data.status not in ("outbid", "won", "buy_now"):
            b.data.status = "lost"
            await Bid.update(b)

    # Get listing for price info
    listing = await listing_get(d.listing_id)
    if not listing:
        return False, f"Listing {d.listing_id} not found"

    # Create order using existing flow
    winning_price = winning_bid.data.amount_per_tonne_eur
    total_eur = winning_bid.data.total_eur
    line_items = [
        OrderLineItem(
            listing_id=d.listing_id,
            quantity=d.quantity_tonnes,
            price_per_tonne=winning_price,
            subtotal=total_eur,
        )
    ]
    order = await order_create(winning_bid.data.bidder_id, line_items, total_eur)

    # Payment: mock mode (Stripe integration follows existing pattern in routes/orders.py)
    mock_id = f"pi_auction_{hashlib.sha256(order.id.encode()).hexdigest()[:16]}"
    await order_set_payment_intent(order.id, mock_id)
    await order_update_status(order.id, "completed")

    # Record ledger entries (TigerBeetle: buyer → escrow → seller)
    await order_record_ledger_entries(order.id)

    # Confirm sale on listing (moves reserved → sold)
    await listing_confirm_sale(d.listing_id, d.quantity_tonnes)

    # Update auction with settlement details
    def _settle(ad: AuctionData) -> Optional[str]:
        ad.status = "settled"
        ad.winner_id = winning_bid.data.bidder_id
        ad.winning_bid_id = winning_bid.id
        ad.winning_price_per_tonne_eur = winning_price
        ad.order_id = order.id
        ad.settled_at = datetime.now(timezone.utc)
        return None

    ok, err = await _auction_cas_retry(auction_id, _settle)
    if ok:
        logger.info(
            f"Auction {auction_id} settled: winner={winning_bid.data.bidder_id}, "
            f"price={winning_price}€/t, order={order.id}"
        )
    return ok, err


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

async def auction_get_bids(
    auction_id: str, limit: int = 100
) -> List[Bid]:
    """Get all bids for an auction, ordered by amount descending."""
    keyspace = Bid.get_keyspace()
    query = (
        f"SELECT META().id, * FROM {keyspace} "
        f"WHERE auction_id = $auction_id "
        f"ORDER BY amount_per_tonne_eur DESC, placed_at ASC "
        f"LIMIT {limit}"
    )
    rows = await keyspace.query(query, auction_id=auction_id)
    return [
        Bid(id=row["id"], data=row.get("bids"))
        for row in rows if row.get("bids")
    ]
