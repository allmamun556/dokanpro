from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_customer_optional, require_tenant
from app.core.rate_limit import limiter
from app.models.customer import Customer
from app.models.order import Order
from app.schemas.order import PublicOrderCreate
from app.schemas.public_order import CheckoutSessionOut, PublicOrderStatusOut
from app.services import public_checkout_service, subscription_service

router = APIRouter(prefix="/checkout", tags=["public-checkout"])
webhook_router = APIRouter(tags=["public-checkout"])


@router.post("", response_model=CheckoutSessionOut)
@limiter.limit("10/minute")
def checkout(
    payload: PublicOrderCreate,
    request: Request,
    db: Session = Depends(get_db),
    customer: Optional[Customer] = Depends(get_current_customer_optional),
):
    # Guest checkout has no customer to read business_id off of — it comes
    # from the /t/{slug}/ site page the order was placed from instead.
    if request.state.business_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unable to determine which restaurant this order belongs to")

    order, checkout_url = public_checkout_service.create_checkout_session(db, payload, customer, request.state.business_id)
    return CheckoutSessionOut(order=order, checkout_url=checkout_url)


@router.get("/{order_id}/status", response_model=PublicOrderStatusOut, dependencies=[Depends(require_tenant)])
def checkout_status(
    order_id: int,
    email: Optional[str] = None,
    db: Session = Depends(get_db),
    customer: Optional[Customer] = Depends(get_current_customer_optional),
):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")

    owns_as_customer = customer is not None and order.customer_id == customer.id
    owns_as_guest = email is not None and order.guest_email is not None and email.lower() == order.guest_email.lower()
    if not (owns_as_customer or owns_as_guest):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")

    return PublicOrderStatusOut(order=order)


@webhook_router.post("/webhooks/stripe", include_in_schema=False)
async def stripe_platform_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Platform-side events on the platform's own Stripe account — subscription
    checkouts and status changes (businesses paying the platform). Diner
    order payments live on connected accounts now, so those events go to
    /webhooks/stripe-connect below instead.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    subscription_service.handle_subscription_webhook_event(db, payload, sig_header)
    return {"status": "ok"}


@webhook_router.post("/webhooks/stripe-connect", include_in_schema=False)
async def stripe_connect_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Diner order payments — these always happen on a connected account now
    (create_checkout_session passes stripe_account=...), and Stripe only
    delivers connected-account events to an endpoint specifically registered
    as a Connect webhook (separate signing secret from the platform's own
    /webhooks/stripe endpoint, which handles subscription events instead).
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    public_checkout_service.handle_webhook_event(db, payload, sig_header)
    return {"status": "ok"}
