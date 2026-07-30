from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import require_tenant
from app.db.session import get_db
from app.schemas.discount import DiscountPreview
from app.services.discount_service import get_active_discount, compute_discount_amount

router = APIRouter(prefix="/discounts", tags=["public-discounts"], dependencies=[Depends(require_tenant)])


def _q2(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@router.get("/lookup/{code}", response_model=DiscountPreview)
def lookup_discount_public(code: str, subtotal: float = Query(..., ge=0), db: Session = Depends(get_db)):
    """Public equivalent of the staff-side coupon lookup — no auth, used by the cart page."""
    subtotal_d = _q2(subtotal)
    discount = get_active_discount(db, code, subtotal_d)
    amount = compute_discount_amount(discount, subtotal_d, cap=subtotal_d)
    return DiscountPreview(
        id=discount.id,
        code=discount.code,
        name=discount.name,
        type=discount.type,
        value=float(discount.value),
        discount_amount=float(amount),
    )
