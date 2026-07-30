from typing import Optional

from sqlalchemy import String, Numeric, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Business(Base):
    """The tenant root. Every other table's business_id points here."""

    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Formerly the singleton BusinessSettings table — folded in here since
    # BusinessSettings was already always id=1, i.e. exactly one business.
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    currency_symbol: Mapped[str] = mapped_column(String(10), default="$")
    default_vat_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    receipt_footer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default="Thank you!")

    # Stripe Connect (Standard) — where this business's own diner payments go.
    # charges_enabled mirrors Stripe's own account flag; checkout is blocked
    # until it's true so diner money never silently lands in the platform's
    # own Stripe balance instead of the restaurant's.
    stripe_account_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_charges_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Stripe Subscriptions — this business paying the platform. Separate
    # Stripe Customer from the Connect account above (different Stripe
    # account entirely: the platform's own, not the restaurant's).
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Stored verbatim as Stripe's own status string (active/past_due/canceled/
    # trialing/...) rather than a duplicated local enum that could drift.
    subscription_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
