import asyncio
import logging
from typing import List, Optional
from datetime import datetime, timezone
from models.entities.couchbase.orders import Order, OrderData, OrderLineItem

logger = logging.getLogger(__name__)


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


async def order_set_payment_link(order_id: str, url: str) -> Optional[Order]:
    order = await Order.get(order_id)
    if not order:
        return None
    order.data.stripe_payment_link_url = url
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


async def order_record_ledger_entries(order_id: str) -> None:
    """Record double-entry ledger transfers in TigerBeetle for a completed order.
    Best-effort: errors are logged but don't block order completion.
    """
    try:
        from clients.tigerbeetle import (
            ensure_platform_account,
            create_transfer,
            PLATFORM_ESCROW_ACCOUNT_ID,
            TRANSFER_CODE_PURCHASE,
            TRANSFER_CODE_SETTLEMENT,
        )
        from models.operations.users import ensure_tigerbeetle_accounts
        from models.operations.listings import listing_get

        order = await Order.get(order_id)
        if not order:
            logger.warning(f"Ledger: order {order_id} not found, skipping")
            return

        loop = asyncio.get_event_loop()

        # Ensure platform escrow account exists
        await loop.run_in_executor(None, ensure_platform_account)

        # Ensure buyer has TB accounts
        buyer_pending_id, buyer_settled_id = await ensure_tigerbeetle_accounts(order.data.buyer_id)

        for li in order.data.line_items:
            listing = await listing_get(li.listing_id)
            if not listing:
                logger.warning(f"Ledger: listing {li.listing_id} not found, skipping line item")
                continue

            seller_id = listing.data.seller_id
            _seller_pending_id, seller_settled_id = await ensure_tigerbeetle_accounts(seller_id)

            amount_cents = int(round(li.subtotal * 100))

            # Transfer 1: buyer settled -> platform escrow (purchase)
            await loop.run_in_executor(
                None,
                create_transfer,
                buyer_settled_id,
                PLATFORM_ESCROW_ACCOUNT_ID,
                amount_cents,
                TRANSFER_CODE_PURCHASE,
            )

            # Transfer 2: platform escrow -> seller settled (settlement)
            await loop.run_in_executor(
                None,
                create_transfer,
                PLATFORM_ESCROW_ACCOUNT_ID,
                seller_settled_id,
                amount_cents,
                TRANSFER_CODE_SETTLEMENT,
            )

            logger.info(
                f"Ledger: buyer {order.data.buyer_id} -> platform -> seller {seller_id} "
                f"amount={amount_cents}c for listing {li.listing_id}"
            )

    except Exception as e:
        logger.error(f"Ledger: failed to record entries for order {order_id}: {e}")
