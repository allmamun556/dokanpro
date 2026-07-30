from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.discount import Discount, DiscountType


def _q2(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def get_active_discount(db: Session, code: str, subtotal: Decimal) -> Discount:
    """Looks up a discount by code and validates it is currently usable against `subtotal`."""
    discount = db.query(Discount).filter(Discount.code == code.strip().upper()).first()
    if discount is None or not discount.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid or inactive discount code")

    now = datetime.now(timezone.utc)
    if discount.starts_at and now < discount.starts_at:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This discount code is not active yet")
    if discount.ends_at and now > discount.ends_at:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This discount code has expired")
    if subtotal < _q2(discount.min_subtotal):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Order subtotal must be at least {_q2(discount.min_subtotal)} to use this code",
        )
    return discount


def compute_discount_amount(discount: Discount, subtotal: Decimal, cap: Decimal) -> Decimal:
    """Computes the discount amount, never exceeding `cap` (e.g. subtotal + tax)."""
    if discount.type == DiscountType.percentage:
        amount = _q2(subtotal * (Decimal(discount.value) / Decimal(100)))
    else:
        amount = _q2(discount.value)
    return min(amount, cap)
