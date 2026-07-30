from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.held_sale import HeldSale
from app.schemas.held_sale import HeldSaleCreate, HeldSaleOut

router = APIRouter(prefix="/held-sales", tags=["held-sales"])


def _to_out(h: HeldSale) -> HeldSaleOut:
    return HeldSaleOut(
        id=h.id,
        store_id=h.store_id,
        customer_id=h.customer_id,
        items=h.items,
        discount_code=h.discount_code,
        note=h.note,
        created_by_name=h.created_by_user.name if h.created_by_user else "Unknown",
        created_at=h.created_at,
    )


@router.get("", response_model=list[HeldSaleOut])
def list_held_sales(store_id: int = 1, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = db.query(HeldSale).filter(HeldSale.store_id == store_id).order_by(HeldSale.created_at.desc()).all()
    return [_to_out(h) for h in rows]


@router.post("", response_model=HeldSaleOut, status_code=status.HTTP_201_CREATED)
def hold_sale(payload: HeldSaleCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not payload.items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot hold an empty cart")
    held = HeldSale(
        business_id=current_user.business_id,
        store_id=payload.store_id,
        customer_id=payload.customer_id,
        items=[item.model_dump() for item in payload.items],
        discount_code=payload.discount_code,
        note=payload.note,
        created_by=current_user.id,
    )
    db.add(held)
    db.commit()
    db.refresh(held)
    return _to_out(held)


@router.delete("/{held_sale_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_held_sale(held_sale_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    held = db.get(HeldSale, held_sale_id)
    if not held:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Held sale not found")
    db.delete(held)
    db.commit()
