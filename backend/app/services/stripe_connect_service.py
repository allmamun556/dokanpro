import stripe
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.business import Business

stripe.api_key = settings.STRIPE_SECRET_KEY


def start_onboarding(db: Session, business: Business) -> str:
    """
    Creates a Standard connected account for this business if it doesn't
    have one yet, then returns a single-use Account Link URL to send them to
    Stripe's hosted onboarding flow — the current Stripe-recommended way to
    collect a Standard account's business/identity details.
    """
    if business.stripe_account_id is None:
        account = stripe.Account.create(
            type="standard",
            business_profile={"name": business.name},
        )
        business.stripe_account_id = account.id
        db.commit()

    return_url = f"{settings.PUBLIC_SITE_URL}/t/{business.slug}/settings.html?stripe_return=1"
    account_link = stripe.AccountLink.create(
        account=business.stripe_account_id,
        type="account_onboarding",
        refresh_url=return_url,
        return_url=return_url,
    )
    return account_link.url


def refresh_account_status(db: Session, business: Business) -> None:
    """Re-fetches the connected account's status from Stripe — called when
    the business returns from the onboarding redirect, or on manual refresh."""
    if business.stripe_account_id is None:
        return
    account = stripe.Account.retrieve(business.stripe_account_id)
    business.stripe_charges_enabled = bool(account.charges_enabled)
    db.commit()
