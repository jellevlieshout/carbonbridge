from typing import List, Optional
from datetime import datetime, timezone
from models.entities.couchbase.orders import Order, OrderData, OrderLineItem


async def order_create(buyer_id: str, line_items: List[OrderLineItem], total_eur: float) -> Order:
    data = OrderData(
        buyer_id=buyer_id,
        line_items=line_items,
        total_eur=total_eur,
        status="pending",
    )
    return await Order.create(data, user_id=buyer_id)


async def order_get(order_id: str) -> Optional[Order]:
    return await Order.get(order_id)


async def order_update_status(order_id: str, status: str) -> Optional[Order]:
    order = await Order.get(order_id)
    if not order:
        return None
    order.data.status = status
    if status == "completed":
        order.data.completed_at = datetime.now(timezone.utc)
    return await Order.update(order)


async def order_set_payment_intent(order_id: str, payment_intent_id: str) -> Optional[Order]:
    order = await Order.get(order_id)
    if not order:
        return None
    order.data.stripe_payment_intent_id = payment_intent_id
    return await Order.update(order)


async def order_update_payment_status(order_id: str, payment_status: str) -> Optional[Order]:
    order = await Order.get(order_id)
    if not order:
        return None
    order.data.stripe_payment_status = payment_status
    return await Order.update(order)


async def order_cancel(order_id: str) -> Optional[Order]:
    order = await Order.get(order_id)
    if not order or order.data.status != "pending":
        return None
    order.data.status = "cancelled"
    return await Order.update(order)


async def order_get_by_buyer(buyer_id: str) -> List[Order]:
    keyspace = Order.get_keyspace()
    query = (
        f"SELECT META().id, * FROM {keyspace} "
        f"WHERE buyer_id = $buyer_id ORDER BY created_at DESC"
    )
    rows = await keyspace.query(query, buyer_id=buyer_id)
    return [
        Order(id=row["id"], data=row.get("orders"))
        for row in rows if row.get("orders")
    ]


async def order_get_by_payment_intent(payment_intent_id: str) -> Optional[Order]:
    keyspace = Order.get_keyspace()
    query = (
        f"SELECT META().id, * FROM {keyspace} "
        f"WHERE stripe_payment_intent_id = $pid LIMIT 1"
    )
    rows = await keyspace.query(query, pid=payment_intent_id)
    for row in rows:
        data_dict = row.get("orders")
        if data_dict:
            return Order(id=row["id"], data=data_dict)
    return None
