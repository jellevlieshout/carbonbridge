from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel
from clients.couchbase import BaseModelCouchbase, BaseCouchbaseEntityData


class OrderLineItem(BaseModel):
    listing_id: str
    quantity: float
    price_per_tonne: float
    subtotal: float


class OrderData(BaseCouchbaseEntityData):
    buyer_id: str
    status: Literal["pending", "confirmed", "completed", "cancelled", "refunded"] = "pending"
    line_items: List[OrderLineItem] = []
    total_eur: float = 0.0
    stripe_payment_intent_id: Optional[str] = None
    stripe_payment_status: Optional[str] = None
    retirement_requested: bool = False
    retirement_reference: Optional[str] = None
    completed_at: Optional[datetime] = None


class Order(BaseModelCouchbase[OrderData]):
    _collection_name = "orders"
