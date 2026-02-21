import asyncio
import hashlib
from typing import List, Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from models.operations.listings import listing_get, listing_update, listing_reserve_quantity
from models.operations.orders import (
    order_create,
    order_get,
    order_get_by_buyer,
    order_cancel,
    order_set_payment_intent,
    order_update_status,
    order_update_payment_status,
    order_record_ledger_entries,
)
from models.entities.couchbase.orders import OrderLineItem
from utils import env, log
from .dependencies import require_authenticated

logger = log.get_logger(__name__)

router = APIRouter(prefix="/orders", tags=["orders"])

STRIPE_SECRET_KEY = env.EnvVarSpec(
    id="STRIPE_SECRET_KEY", is_optional=True, is_secret=True
)


def _stripe_configured() -> bool:
    return bool(env.parse(STRIPE_SECRET_KEY))


def _get_stripe():
    key = env.parse(STRIPE_SECRET_KEY)
    if not key:
        raise HTTPException(status_code=503, detail="Stripe is not configured")
    stripe.api_key = key
    return stripe


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class OrderLineItemRequest(BaseModel):
    listing_id: str
    quantity: float


class CreateOrderRequest(BaseModel):
    line_items: List[OrderLineItemRequest]
    retirement_requested: bool = False


class OrderLineItemResponse(BaseModel):
    listing_id: str
    quantity: float
    price_per_tonne: float
    subtotal: float


class OrderResponse(BaseModel):
    id: str
    buyer_id: str
    status: str
    line_items: List[OrderLineItemResponse]
    total_eur: float
    stripe_payment_intent_id: Optional[str] = None
    stripe_client_secret: Optional[str] = None
    retirement_requested: bool = False


def _order_to_response(order, client_secret: Optional[str] = None) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        buyer_id=order.data.buyer_id,
        status=order.data.status,
        line_items=[
            OrderLineItemResponse(**li.model_dump())
            for li in order.data.line_items
        ],
        total_eur=order.data.total_eur,
        stripe_payment_intent_id=order.data.stripe_payment_intent_id,
        stripe_client_secret=client_secret,
        retirement_requested=order.data.retirement_requested,
    )


# ---------------------------------------------------------------------------
# POST /orders — create order + PaymentIntent
# ---------------------------------------------------------------------------

@router.post("/", response_model=OrderResponse, status_code=201)
async def route_order_create(
    body: CreateOrderRequest,
    user: dict = Depends(require_authenticated),
):
    buyer_id = user["sub"]

    built_items: List[OrderLineItem] = []
    total_eur = 0.0

    for item in body.line_items:
        listing = await listing_get(item.listing_id)
        if not listing:
            raise HTTPException(status_code=404, detail=f"Listing {item.listing_id} not found")
        if listing.data.status != "active":
            raise HTTPException(status_code=400, detail=f"Listing {item.listing_id} is not active")

        available = listing.data.quantity_tonnes - listing.data.quantity_reserved - listing.data.quantity_sold
        if item.quantity > available:
            raise HTTPException(
                status_code=400,
                detail=f"Listing {item.listing_id}: requested {item.quantity}t but only {available}t available",
            )

        reserved = await listing_reserve_quantity(item.listing_id, item.quantity)
        if not reserved:
            raise HTTPException(
                status_code=409,
                detail=f"Could not reserve {item.quantity}t on listing {item.listing_id}",
            )

        subtotal = round(item.quantity * listing.data.price_per_tonne_eur, 2)
        total_eur += subtotal
        built_items.append(OrderLineItem(
            listing_id=item.listing_id,
            quantity=item.quantity,
            price_per_tonne=listing.data.price_per_tonne_eur,
            subtotal=subtotal,
        ))

    total_eur = round(total_eur, 2)

    # Create order in Couchbase
    order = await order_create(buyer_id, built_items, total_eur)

    # Set retirement flag
    if body.retirement_requested:
        order.data.retirement_requested = True
        from models.entities.couchbase.orders import Order
        await Order.update(order)

    # Create Stripe PaymentIntent or use mock
    client_secret = None
    if _stripe_configured():
        s = _get_stripe()
        intent = s.PaymentIntent.create(
            amount=int(total_eur * 100),  # Stripe uses cents
            currency="eur",
            metadata={
                "carbonbridge_order_id": order.id,
                "buyer_id": buyer_id,
            },
        )
        await order_set_payment_intent(order.id, intent.id)
        order.data.stripe_payment_intent_id = intent.id
        client_secret = intent.client_secret
    else:
        # Mock mode: generate a fake intent ID
        mock_id = f"pi_mock_{hashlib.sha256(order.id.encode()).hexdigest()[:16]}"
        await order_set_payment_intent(order.id, mock_id)
        order.data.stripe_payment_intent_id = mock_id
        client_secret = f"mock_secret_{mock_id}"
        logger.info(f"Mock mode: order {order.id} using fake intent {mock_id}")

    return _order_to_response(order, client_secret=client_secret)


# ---------------------------------------------------------------------------
# GET /orders — list buyer's orders
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[OrderResponse])
async def route_orders_list(user: dict = Depends(require_authenticated)):
    buyer_id = user["sub"]
    orders = await order_get_by_buyer(buyer_id)
    return [_order_to_response(o) for o in orders]


# ---------------------------------------------------------------------------
# GET /orders/{id} — get single order
# ---------------------------------------------------------------------------

@router.get("/{order_id}", response_model=OrderResponse)
async def route_order_get(
    order_id: str,
    user: dict = Depends(require_authenticated),
):
    order = await order_get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.data.buyer_id != user["sub"]:
        raise HTTPException(status_code=403, detail="Not your order")
    return _order_to_response(order)


# ---------------------------------------------------------------------------
# POST /orders/{id}/cancel — cancel pending order
# ---------------------------------------------------------------------------

@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def route_order_cancel(
    order_id: str,
    user: dict = Depends(require_authenticated),
):
    order = await order_get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.data.buyer_id != user["sub"]:
        raise HTTPException(status_code=403, detail="Not your order")
    if order.data.status != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot cancel order with status '{order.data.status}'")

    # Release reserved quantities
    for li in order.data.line_items:
        await listing_reserve_quantity(li.listing_id, -li.quantity)

    # Cancel Stripe PaymentIntent if exists
    if order.data.stripe_payment_intent_id:
        try:
            s = _get_stripe()
            s.PaymentIntent.cancel(order.data.stripe_payment_intent_id)
        except Exception as e:
            logger.warning(f"Failed to cancel PaymentIntent: {e}")

    cancelled = await order_cancel(order_id)
    return _order_to_response(cancelled)


# ---------------------------------------------------------------------------
# POST /orders/{id}/mock-confirm — simulate payment success (dev only)
# ---------------------------------------------------------------------------

@router.post("/{order_id}/mock-confirm", response_model=OrderResponse)
async def route_order_mock_confirm(
    order_id: str,
    user: dict = Depends(require_authenticated),
):
    """Simulate a successful payment after 2-3 seconds. Only works when Stripe is not configured."""
    if _stripe_configured():
        raise HTTPException(status_code=400, detail="Mock confirm disabled — Stripe is configured")

    order = await order_get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.data.buyer_id != user["sub"]:
        raise HTTPException(status_code=403, detail="Not your order")
    if order.data.status != "pending":
        raise HTTPException(status_code=400, detail=f"Order is not pending (status: {order.data.status})")

    # Simulate processing delay
    await asyncio.sleep(2.5)

    # Mark payment as succeeded
    await order_update_payment_status(order.id, "succeeded")
    await order_update_status(order.id, "completed")
    await order_record_ledger_entries(order.id)

    # Move reserved → sold on each listing
    for li in order.data.line_items:
        listing = await listing_get(li.listing_id)
        if listing:
            listing.data.quantity_reserved -= li.quantity
            listing.data.quantity_sold += li.quantity
            if listing.data.quantity_sold >= listing.data.quantity_tonnes:
                listing.data.status = "sold_out"
            await listing_update(listing)

    updated = await order_get(order_id)
    logger.info(f"Mock payment confirmed for order {order_id}")
    return _order_to_response(updated)
