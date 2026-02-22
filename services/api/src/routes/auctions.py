"""
API endpoints for auctions and bidding.

POST   /auctions/              — create auction from a listing (seller)
GET    /auctions/              — search active auctions (public)
GET    /auctions/me            — seller's own auctions
GET    /auctions/{id}          — auction detail with listing metadata
GET    /auctions/{id}/bids     — bid history
POST   /auctions/{id}/bid      — place a bid
POST   /auctions/{id}/buy-now  — instant purchase at buy-now price
POST   /auctions/{id}/cancel   — cancel auction (no bids only)
GET    /auctions/{id}/stream   — SSE stream for live bid updates
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from models.entities.couchbase.auctions import AuctionConfig
from models.operations.auctions import (
    auction_create,
    auction_get,
    auction_search,
    auction_get_by_seller,
    auction_place_bid,
    auction_cancel,
    auction_get_bids,
    auction_settle,
)
from models.operations.listings import listing_get
from utils import log

from .dependencies import require_authenticated, require_seller

logger = log.get_logger(__name__)

router = APIRouter(prefix="/auctions", tags=["auctions"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class CreateAuctionRequest(BaseModel):
    listing_id: str
    starting_price_per_tonne_eur: float
    reserve_price_per_tonne_eur: Optional[float] = None
    buy_now_price_per_tonne_eur: Optional[float] = None
    min_bid_increment_eur: float = 0.50
    quantity_tonnes: float
    duration_hours: float = 48.0
    auto_extend_minutes: int = 5


class PlaceBidRequest(BaseModel):
    amount_per_tonne_eur: float


class BidResponse(BaseModel):
    id: str
    auction_id: str
    bidder_id: str
    amount_per_tonne_eur: float
    total_eur: float
    placed_at: Optional[datetime] = None
    placed_by: str
    status: str
    is_buy_now: bool


class AuctionConfigResponse(BaseModel):
    auction_type: str
    starting_price_per_tonne_eur: float
    reserve_price_per_tonne_eur: Optional[float] = None
    buy_now_price_per_tonne_eur: Optional[float] = None
    min_bid_increment_eur: float
    auto_extend_minutes: int
    auto_extend_duration_minutes: int


class AuctionResponse(BaseModel):
    id: str
    seller_id: str
    listing_id: str
    created_by: str
    config: AuctionConfigResponse
    quantity_tonnes: float
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    effective_ends_at: Optional[datetime] = None
    extensions_count: int
    status: str
    current_high_bid_eur: Optional[float] = None
    current_high_bidder_id: Optional[str] = None
    bid_count: int
    winner_id: Optional[str] = None
    winning_price_per_tonne_eur: Optional[float] = None
    order_id: Optional[str] = None
    settled_at: Optional[datetime] = None
    # Joined listing metadata
    project_name: Optional[str] = None
    project_type: Optional[str] = None
    project_country: Optional[str] = None
    vintage_year: Optional[int] = None
    co_benefits: List[str] = []
    verification_status: Optional[str] = None


async def _auction_to_response(auction) -> AuctionResponse:
    """Convert an Auction entity to a response, joining listing metadata."""
    d = auction.data
    listing = await listing_get(d.listing_id)
    ld = listing.data if listing else None

    return AuctionResponse(
        id=auction.id,
        seller_id=d.seller_id,
        listing_id=d.listing_id,
        created_by=d.created_by,
        config=AuctionConfigResponse(
            auction_type=d.config.auction_type,
            starting_price_per_tonne_eur=d.config.starting_price_per_tonne_eur,
            reserve_price_per_tonne_eur=d.config.reserve_price_per_tonne_eur,
            buy_now_price_per_tonne_eur=d.config.buy_now_price_per_tonne_eur,
            min_bid_increment_eur=d.config.min_bid_increment_eur,
            auto_extend_minutes=d.config.auto_extend_minutes,
            auto_extend_duration_minutes=d.config.auto_extend_duration_minutes,
        ),
        quantity_tonnes=d.quantity_tonnes,
        starts_at=d.starts_at,
        ends_at=d.ends_at,
        effective_ends_at=d.effective_ends_at,
        extensions_count=d.extensions_count,
        status=d.status,
        current_high_bid_eur=d.current_high_bid_eur,
        current_high_bidder_id=d.current_high_bidder_id,
        bid_count=d.bid_count,
        winner_id=d.winner_id,
        winning_price_per_tonne_eur=d.winning_price_per_tonne_eur,
        order_id=d.order_id,
        settled_at=d.settled_at,
        project_name=ld.project_name if ld else None,
        project_type=ld.project_type if ld else None,
        project_country=ld.project_country if ld else None,
        vintage_year=ld.vintage_year if ld else None,
        co_benefits=ld.co_benefits if ld else [],
        verification_status=ld.verification_status if ld else None,
    )


def _bid_to_response(bid) -> BidResponse:
    d = bid.data
    return BidResponse(
        id=bid.id,
        auction_id=d.auction_id,
        bidder_id=d.bidder_id,
        amount_per_tonne_eur=d.amount_per_tonne_eur,
        total_eur=d.total_eur,
        placed_at=d.placed_at,
        placed_by=d.placed_by,
        status=d.status,
        is_buy_now=d.is_buy_now,
    )


# ---------------------------------------------------------------------------
# POST /auctions/ — create auction
# ---------------------------------------------------------------------------

@router.post("/", response_model=AuctionResponse, status_code=201)
async def route_auction_create(
    body: CreateAuctionRequest,
    user: dict = Depends(require_seller),
):
    """Create an auction from a listing. Reserves the auctioned quantity."""
    seller_id = user["sub"]
    now = datetime.now(timezone.utc)

    config = AuctionConfig(
        starting_price_per_tonne_eur=body.starting_price_per_tonne_eur,
        reserve_price_per_tonne_eur=body.reserve_price_per_tonne_eur,
        buy_now_price_per_tonne_eur=body.buy_now_price_per_tonne_eur,
        min_bid_increment_eur=body.min_bid_increment_eur,
        auto_extend_minutes=body.auto_extend_minutes,
    )

    try:
        auction = await auction_create(
            seller_id=seller_id,
            listing_id=body.listing_id,
            config=config,
            quantity_tonnes=body.quantity_tonnes,
            starts_at=now,  # start immediately
            ends_at=now + timedelta(hours=body.duration_hours),
            created_by="human",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return await _auction_to_response(auction)


# ---------------------------------------------------------------------------
# GET /auctions/ — search active auctions
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[AuctionResponse])
async def route_auctions_search(
    status: str = "active",
    project_type: Optional[str] = None,
    limit: int = Query(default=50, le=100),
):
    """Search auctions with optional filters."""
    auctions = await auction_search(
        status=status,
        project_type=project_type,
        limit=limit,
    )
    return [await _auction_to_response(a) for a in auctions]


# ---------------------------------------------------------------------------
# GET /auctions/me — seller's own auctions
# ---------------------------------------------------------------------------

@router.get("/me", response_model=List[AuctionResponse])
async def route_auctions_mine(user: dict = Depends(require_seller)):
    """List the seller's own auctions."""
    seller_id = user["sub"]
    auctions = await auction_get_by_seller(seller_id)
    return [await _auction_to_response(a) for a in auctions]


# ---------------------------------------------------------------------------
# GET /auctions/{id} — auction detail
# ---------------------------------------------------------------------------

@router.get("/{auction_id}", response_model=AuctionResponse)
async def route_auction_detail(auction_id: str):
    """Get a single auction with listing metadata."""
    auction = await auction_get(auction_id)
    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")
    return await _auction_to_response(auction)


# ---------------------------------------------------------------------------
# GET /auctions/{id}/bids — bid history
# ---------------------------------------------------------------------------

@router.get("/{auction_id}/bids", response_model=List[BidResponse])
async def route_auction_bids(auction_id: str):
    """Get bid history for an auction, ordered by amount descending."""
    auction = await auction_get(auction_id)
    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")
    bids = await auction_get_bids(auction_id)
    return [_bid_to_response(b) for b in bids]


# ---------------------------------------------------------------------------
# POST /auctions/{id}/bid — place a bid
# ---------------------------------------------------------------------------

@router.post("/{auction_id}/bid", response_model=BidResponse, status_code=201)
async def route_place_bid(
    auction_id: str,
    body: PlaceBidRequest,
    user: dict = Depends(require_authenticated),
):
    """Place a bid on an active auction."""
    bidder_id = user["sub"]

    bid, err = await auction_place_bid(
        auction_id=auction_id,
        bidder_id=bidder_id,
        amount_per_tonne_eur=body.amount_per_tonne_eur,
        placed_by="human",
    )
    if err:
        raise HTTPException(status_code=400, detail=err)

    # If buy-now triggered, settle immediately
    if bid.data.is_buy_now:
        ok, settle_err = await auction_settle(auction_id)
        if not ok:
            logger.error(f"Buy-now settlement failed for auction {auction_id}: {settle_err}")

    return _bid_to_response(bid)


# ---------------------------------------------------------------------------
# POST /auctions/{id}/buy-now — instant purchase
# ---------------------------------------------------------------------------

@router.post("/{auction_id}/buy-now", response_model=BidResponse, status_code=201)
async def route_buy_now(
    auction_id: str,
    user: dict = Depends(require_authenticated),
):
    """Instantly purchase at the buy-now price."""
    auction = await auction_get(auction_id)
    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")
    if not auction.data.config.buy_now_price_per_tonne_eur:
        raise HTTPException(status_code=400, detail="This auction has no buy-now price")

    bidder_id = user["sub"]

    bid, err = await auction_place_bid(
        auction_id=auction_id,
        bidder_id=bidder_id,
        amount_per_tonne_eur=auction.data.config.buy_now_price_per_tonne_eur,
        placed_by="human",
    )
    if err:
        raise HTTPException(status_code=400, detail=err)

    # Settle immediately
    ok, settle_err = await auction_settle(auction_id)
    if not ok:
        logger.error(f"Buy-now settlement failed for auction {auction_id}: {settle_err}")

    return _bid_to_response(bid)


# ---------------------------------------------------------------------------
# POST /auctions/{id}/cancel — cancel auction
# ---------------------------------------------------------------------------

@router.post("/{auction_id}/cancel", response_model=AuctionResponse)
async def route_auction_cancel(
    auction_id: str,
    user: dict = Depends(require_seller),
):
    """Cancel an auction. Only allowed if no bids have been placed."""
    auction = await auction_get(auction_id)
    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")
    if auction.data.seller_id != user["sub"]:
        raise HTTPException(status_code=403, detail="Not your auction")

    ok, err = await auction_cancel(auction_id)
    if not ok:
        raise HTTPException(status_code=400, detail=err)

    updated = await auction_get(auction_id)
    return await _auction_to_response(updated)


# ---------------------------------------------------------------------------
# GET /auctions/{id}/stream — SSE for live bid updates
# ---------------------------------------------------------------------------

@router.get("/{auction_id}/stream")
async def route_auction_stream(auction_id: str):
    """Server-Sent Events stream for live auction updates.

    Polls Couchbase every 1 second and emits update events when bid_count
    changes. Emits an ended event when the auction status leaves active.
    """
    async def event_generator():
        last_bid_count = -1
        while True:
            auction = await auction_get(auction_id)
            if not auction:
                yield f"event: error\ndata: {json.dumps({'error': 'Auction not found'})}\n\n"
                break

            d = auction.data

            # Emit update when bid count changes or on first poll
            if d.bid_count != last_bid_count:
                last_bid_count = d.bid_count
                yield (
                    f"event: update\n"
                    f"data: {json.dumps({
                        'auction_id': auction_id,
                        'status': d.status,
                        'current_high_bid_eur': d.current_high_bid_eur,
                        'current_high_bidder_id': d.current_high_bidder_id,
                        'bid_count': d.bid_count,
                        'effective_ends_at': d.effective_ends_at.isoformat() if d.effective_ends_at else None,
                        'extensions_count': d.extensions_count,
                    })}\n\n"
                )

            # Check if auction has ended
            if d.status not in ("active", "scheduled"):
                yield (
                    f"event: ended\n"
                    f"data: {json.dumps({
                        'status': d.status,
                        'winner_id': d.winner_id,
                        'winning_price_per_tonne_eur': d.winning_price_per_tonne_eur,
                        'order_id': d.order_id,
                    })}\n\n"
                )
                break

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
