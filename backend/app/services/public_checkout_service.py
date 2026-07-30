from typing import Optional
from urllib.parse import quote

import stripe
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.business import Business
from app.models.customer import Customer
from app.models.notification import NotificationChannel
from app.models.order import Order, OrderStatus, FulfillmentStatus
from app.schemas.order import PublicOrderCreate
from app.services import order_service, notification_service, ws_manager

stripe.api_key = settings.STRIPE_SECRET_KEY

CURRENCY = "eur"


def create_checkout_session(
    db: Session, order_in: PublicOrderCreate, customer: Optional[Customer], business_id: int
) -> tuple[Order, str]:
    business = db.get(Business, business_id)
    if not business.stripe_account_id or not business.stripe_charges_enabled:
        # Never silently take a diner's payment into the platform's own
        # Stripe balance — if this business hasn't finished connecting their
        # own account, online payment simply isn't available yet.
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This restaurant hasn't finished setting up online payments yet",
        )

    # Reserves stock and creates the Order in fulfillment_status=pending first,
    # so the Stripe redirect can never oversell the last portion of a dish.
    order = order_service.create_public_order(db, order_in, customer, business_id)

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": CURRENCY,
                        "product_data": {"name": f"{business.name} — Order #{order.id}"},
                        "unit_amount": int(round(float(order.total) * 100)),
                    },
                    "quantity": 1,
                }
            ],
            metadata={"order_id": str(order.id)},
            success_url=(
                f"{settings.PUBLIC_SITE_URL}/t/{business.slug}/site/order-status.html?order_id={order.id}"
                f"&email={quote(order.guest_email or '')}"
            ),
            cancel_url=f"{settings.PUBLIC_SITE_URL}/t/{business.slug}/site/cart.html?order_id={order.id}",
            # Standard connected account: making this call "as" the connected
            # account means the charge lands directly in their Stripe balance,
            # not the platform's — no application fee, no platform funds involved.
            stripe_account=business.stripe_account_id,
        )
    except stripe.error.StripeError as e:
        # Don't leave an orphaned order with reserved stock, no way to pay, and
        # a status that would still count it as revenue in reports.
        order_service.reverse_order_stock(db, order, reference=f"order:{order.id}:payment_failed")
        order.fulfillment_status = FulfillmentStatus.cancelled
        order.status = OrderStatus.voided
        db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Could not start payment: {e.user_message or str(e)}")

    order.stripe_payment_intent_id = session.payment_intent or session.id
    db.commit()
    db.refresh(order)

    return order, session.url


def handle_webhook_event(db: Session, payload: bytes, sig_header: str) -> None:
    """
    Handles events from the Connect webhook endpoint (/webhooks/stripe-connect)
    — diner order payments, which now always happen on a connected account
    rather than the platform's own. Order lookup by metadata.order_id works
    identically regardless of which connected account the event came from.
    """
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_CONNECT_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid Stripe webhook payload/signature")

    session = event["data"]["object"]
    order_id = session.get("metadata", {}).get("order_id")
    if order_id is None:
        return

    order = db.get(Order, int(order_id))
    if order is None or order.fulfillment_status != FulfillmentStatus.pending:
        return

    if event["type"] == "checkout.session.completed":
        order.fulfillment_status = FulfillmentStatus.confirmed
        notification_service.send(
            db,
            recipient_email=order.guest_email or (order.customer.email if order.customer else None),
            channel=NotificationChannel.email,
            event_type="order_confirmed",
            subject=f"Order #{order.id} confirmed",
            body=f"Your order #{order.id} has been received and is being prepared. Total: €{order.total}.",
            business_id=order.business_id,
        )
        db.commit()
        ws_manager.broadcast({"type": "order_updated", "order_id": order.id}, business_id=order.business_id)
    elif event["type"] in ("checkout.session.expired",):
        # Customer never paid — reverse the stock reservation and void the
        # order so it's excluded from revenue reports (same as a staff void).
        order_service.reverse_order_stock(db, order, reference=f"order:{order.id}:payment_expired")
        order.fulfillment_status = FulfillmentStatus.cancelled
        order.status = OrderStatus.voided
        db.commit()
