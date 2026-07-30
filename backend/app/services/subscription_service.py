import stripe
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.business import Business

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_subscription_checkout(db: Session, business: Business, admin_email: str) -> str:
    """
    Platform-side billing: this business paying the platform a flat monthly
    fee. Runs on the platform's own Stripe account (no stripe_account param)
    — entirely separate from their Connect account, which is where their
    own diners' money goes.
    """
    if not settings.STRIPE_SUBSCRIPTION_PRICE_ID:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Billing isn't configured yet")

    if business.stripe_customer_id is None:
        customer = stripe.Customer.create(
            email=admin_email,
            name=business.name,
            metadata={"business_id": str(business.id)},
        )
        business.stripe_customer_id = customer.id
        db.commit()

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=business.stripe_customer_id,
        line_items=[{"price": settings.STRIPE_SUBSCRIPTION_PRICE_ID, "quantity": 1}],
        metadata={"business_id": str(business.id)},
        success_url=f"{settings.PUBLIC_SITE_URL}/t/{business.slug}/settings.html?billing_return=1",
        cancel_url=f"{settings.PUBLIC_SITE_URL}/t/{business.slug}/settings.html",
    )
    return session.url


def handle_subscription_webhook_event(db: Session, payload: bytes, sig_header: str) -> None:
    """
    Platform-side events: subscription checkout completion and status
    changes. Verified against the platform's own webhook secret (this
    endpoint never sees connected-account events — those go to
    /webhooks/stripe-connect instead, a separate Stripe webhook registration).
    """
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid Stripe webhook payload/signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        if session.get("mode") != "subscription":
            return
        business_id = session.get("metadata", {}).get("business_id")
        if business_id is None:
            return
        business = db.get(Business, int(business_id))
        if business is None:
            return
        business.stripe_subscription_id = session.get("subscription")
        business.subscription_status = "active"
        db.commit()

    elif event["type"] in ("customer.subscription.updated", "customer.subscription.deleted"):
        subscription = event["data"]["object"]
        business = db.query(Business).filter(Business.stripe_subscription_id == subscription["id"]).first()
        if business is None:
            return
        business.subscription_status = subscription.get("status", "canceled")
        db.commit()
