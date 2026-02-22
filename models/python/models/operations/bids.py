"""
Bid query operations.

Simple CRUD — the heavy bid-placement logic lives in operations/auctions.py.
"""

from typing import List, Optional

from models.entities.couchbase.bids import Bid


async def bid_get(bid_id: str) -> Optional[Bid]:
    return await Bid.get(bid_id)


async def bid_get_by_auction(auction_id: str, limit: int = 100) -> List[Bid]:
    """Get bids for an auction, ordered by amount descending."""
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


async def bid_get_by_bidder(bidder_id: str, limit: int = 50) -> List[Bid]:
    """Get a bidder's bid history, ordered by most recent first."""
    keyspace = Bid.get_keyspace()
    query = (
        f"SELECT META().id, * FROM {keyspace} "
        f"WHERE bidder_id = $bidder_id "
        f"ORDER BY placed_at DESC "
        f"LIMIT {limit}"
    )
    rows = await keyspace.query(query, bidder_id=bidder_id)
    return [
        Bid(id=row["id"], data=row.get("bids"))
        for row in rows if row.get("bids")
    ]
