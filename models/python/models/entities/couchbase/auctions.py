from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel
from clients.couchbase import BaseModelCouchbase, BaseCouchbaseEntityData


class AuctionConfig(BaseModel):
    """Immutable auction parameters set at creation time."""
    auction_type: Literal["english"] = "english"
    starting_price_per_tonne_eur: float
    reserve_price_per_tonne_eur: Optional[float] = None
    buy_now_price_per_tonne_eur: Optional[float] = None
    min_bid_increment_eur: float = 0.50
    auto_extend_minutes: int = 5
    auto_extend_duration_minutes: int = 5


class AuctionData(BaseCouchbaseEntityData):
    # Ownership
    seller_id: str
    listing_id: str
    created_by: Literal["human", "agent"] = "human"
    agent_run_id: Optional[str] = None

    # Auction config (immutable after creation)
    config: AuctionConfig

    # Quantity being auctioned (carved from the listing via listing_reserve_quantity)
    quantity_tonnes: float

    # Schedule
    starts_at: datetime
    ends_at: datetime
    effective_ends_at: datetime  # may be extended by anti-snipe
    extensions_count: int = 0

    # Current state
    status: Literal[
        "scheduled",
        "active",
        "ended",
        "settled",
        "failed",
        "cancelled",
        "bought_now",
    ] = "scheduled"

    # Denormalized high-bid (updated atomically via CAS on each bid)
    current_high_bid_eur: Optional[float] = None
    current_high_bid_id: Optional[str] = None
    current_high_bidder_id: Optional[str] = None
    bid_count: int = 0

    # Settlement
    winner_id: Optional[str] = None
    winning_bid_id: Optional[str] = None
    winning_price_per_tonne_eur: Optional[float] = None
    order_id: Optional[str] = None
    settled_at: Optional[datetime] = None


class Auction(BaseModelCouchbase[AuctionData]):
    _collection_name = "auctions"
