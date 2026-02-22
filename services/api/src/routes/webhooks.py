import stripe

from fastapi import APIRouter, HTTPException, Request
from models.operations.orders import (
    order_get_by_payment_intent,
    order_update_status,
    order_update_payment_status,
    order_record_ledger_entries,
)
from models.operations.listings import listing_confirm_sale
from utils import env, log

logger = log.get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

STRIPE_SECRET_KEY = env.EnvVarSpec(
    id="STRIPE_SECRET_KEY", is_optional=True, is_secret=True
)
STRIPE_WEBHOOK_SECRET = env.EnvVarSpec(
    id="STRIPE_WEBHOOK_SECRET", is_optional=True, is_secret=True
)


@router.post("/stripe")
async def route_stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    secret_key = env.parse(STRIPE_SECRET_KEY)
    webhook_secret = env.parse(STRIPE_WEBHOOK_SECRET)

    if not secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    stripe.api_key = secret_key

    # Verify webhook signature if secret is configured
    if webhook_secret and sig_header:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")
    else:
        import json
        event = json.loads(payload)

    event_type = event.get("type") if isinstance(event, dict) else event.type
    data_object = event.get("data", {}).get("object", {}) if isinstance(event, dict) else event.data.object

    if event_type == "payment_intent.succeeded":
        payment_intent_id = data_object.get("id") if isinstance(data_object, dict) else data_object.id
        logger.info(f"Payment succeeded for intent {payment_intent_id}")

        order = await order_get_by_payment_intent(payment_intent_id)
        if not order:
            logger.warning(f"No order found for payment intent {payment_intent_id}")
            return {"status": "ok"}

        # Update order status
        await order_update_payment_status(order.id, "succeeded")
        await order_update_status(order.id, "completed")
        await order_record_ledger_entries(order.id)

        # Move reserved → sold on each listing
        for li in order.data.line_items:
            await listing_confirm_sale(li.listing_id, li.quantity)

        logger.info(f"Order {order.id} completed via webhook")

    elif event_type == "payment_intent.payment_failed":
        payment_intent_id = data_object.get("id") if isinstance(data_object, dict) else data_object.id
        logger.info(f"Payment failed for intent {payment_intent_id}")

        order = await order_get_by_payment_intent(payment_intent_id)
        if order:
            await order_update_payment_status(order.id, "failed")

    return {"status": "ok"}
