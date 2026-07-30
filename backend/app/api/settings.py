from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_permission
from app.models.user import User
from app.models.business import Business
from app.schemas.settings import (
    BusinessSettingsUpdate, BusinessSettingsOut, StripeConnectStatus, StripeOnboardingOut,
)
from app.services.audit_service import log_action
from app.services import stripe_connect_service

router = APIRouter(prefix="/settings", tags=["settings"])
MANAGE = Depends(require_permission("settings.manage"))


def _to_out(business: Business) -> BusinessSettingsOut:
    return BusinessSettingsOut(
        business_name=business.name,
        address=business.address,
        currency_symbol=business.currency_symbol,
        default_vat_rate=business.default_vat_rate,
        receipt_footer=business.receipt_footer,
    )


@router.get("", response_model=BusinessSettingsOut)
def get_settings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    business = db.get(Business, current_user.business_id)
    return _to_out(business)


@router.patch("", response_model=BusinessSettingsOut, dependencies=[Depends(require_permission("settings.manage"))])
def update_settings(payload: BusinessSettingsUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    business = db.get(Business, current_user.business_id)
    updates = payload.model_dump(exclude_unset=True)
    if "business_name" in updates:
        business.name = updates.pop("business_name")
    for field, value in updates.items():
        setattr(business, field, value)
    log_action(db, current_user.id, "update", "settings", business.id, business_id=current_user.business_id)
    db.commit()
    db.refresh(business)
    return _to_out(business)


@router.post("/stripe/connect", response_model=StripeOnboardingOut, dependencies=[MANAGE])
def start_stripe_connect(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    business = db.get(Business, current_user.business_id)
    url = stripe_connect_service.start_onboarding(db, business)
    return StripeOnboardingOut(onboarding_url=url)


@router.get("/stripe/connect/status", response_model=StripeConnectStatus)
def get_stripe_connect_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    business = db.get(Business, current_user.business_id)
    if business.stripe_account_id is not None:
        stripe_connect_service.refresh_account_status(db, business)
    return StripeConnectStatus(
        connected=business.stripe_account_id is not None,
        charges_enabled=business.stripe_charges_enabled,
    )
