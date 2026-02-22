from typing import Optional, Literal
from datetime import datetime
from clients.couchbase import BaseModelCouchbase, BaseCouchbaseEntityData


class BidData(BaseCouchbaseEntityData):
    auction_id: str
    bidder_id: str
    amount_per_tonne_eur: float
    total_eur: float  # amount_per_tonne * auction.quantity_tonnes
    placed_at: datetime
    placed_by: Literal["human", "agent"] = "human"
    agent_run_id: Optional[str] = None
    status: Literal["active", "outbid", "won", "lost", "buy_now"] = "active"
    is_buy_now: bool = False


class Bid(BaseModelCouchbase[BidData]):
    _collection_name = "bids"
