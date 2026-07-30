from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_permission
from app.models.user import User
from app.models.business import Business
from app.schemas.billing import SubscriptionStatusOut, SubscribeCheckoutOut
from app.services import subscription_service

router = APIRouter(prefix="/billing", tags=["billing"])
MANAGE = Depends(require_permission("settings.manage"))


@router.get("/status", response_model=SubscriptionStatusOut)
def get_subscription_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    business = db.get(Business, current_user.business_id)
    return SubscriptionStatusOut(
        subscribed=business.subscription_status == "active",
        status=business.subscription_status,
    )


@router.post("/subscribe", response_model=SubscribeCheckoutOut, dependencies=[MANAGE])
def subscribe(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    business = db.get(Business, current_user.business_id)
    url = subscription_service.create_subscription_checkout(db, business, current_user.email)
    return SubscribeCheckoutOut(checkout_url=url)
