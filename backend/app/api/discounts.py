from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_permission
from app.models.user import User
from app.models.discount import Discount
from app.schemas.discount import DiscountCreate, DiscountUpdate, DiscountOut, DiscountPreview
from app.services.discount_service import get_active_discount, compute_discount_amount
from app.services.audit_service import log_action

router = APIRouter(prefix="/discounts", tags=["discounts"])

MANAGE = Depends(require_permission("discounts.manage"))


def _q2(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@router.get("", response_model=list[DiscountOut], dependencies=[MANAGE])
def list_discounts(db: Session = Depends(get_db)):
    return db.query(Discount).order_by(Discount.id.desc()).all()


@router.post("", response_model=DiscountOut, status_code=status.HTTP_201_CREATED, dependencies=[MANAGE])
def create_discount(payload: DiscountCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    discount = Discount(business_id=current_user.business_id, **payload.model_dump())
    db.add(discount)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A discount with this code already exists")
    db.refresh(discount)
    log_action(db, current_user.id, "create", "discount", discount.id, {"code": discount.code}, business_id=current_user.business_id)
    db.commit()
    return discount


@router.patch("/{discount_id}", response_model=DiscountOut, dependencies=[MANAGE])
def update_discount(discount_id: int, payload: DiscountUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    discount = db.get(Discount, discount_id)
    if not discount:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Discount not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(discount, field, value)
    log_action(db, current_user.id, "update", "discount", discount.id, payload.model_dump(exclude_unset=True), business_id=current_user.business_id)
    db.commit()
    db.refresh(discount)
    return discount


@router.delete("/{discount_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[MANAGE])
def delete_discount(discount_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    discount = db.get(Discount, discount_id)
    if not discount:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Discount not found")
    db.delete(discount)
    log_action(db, current_user.id, "delete", "discount", discount_id, {"code": discount.code}, business_id=current_user.business_id)
    db.commit()


@router.get("/lookup/{code}", response_model=DiscountPreview)
def lookup_discount(
    code: str,
    subtotal: float = Query(..., ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Used by the POS screen to validate a code and preview its discount amount before checkout."""
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
