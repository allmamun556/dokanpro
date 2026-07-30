from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_permission
from app.models.user import User
from app.models.purchase import Purchase
from app.schemas.purchase import (
    PurchaseCreate, PurchaseOut, PurchaseReturnCreate, PurchaseReturnOut,
    PurchasePaymentCreate, PurchasePaymentOut,
)
from app.services.purchase_service import create_purchase, return_purchase_items, record_purchase_payment

router = APIRouter(prefix="/purchases", tags=["purchases"])

MANAGE = Depends(require_permission("purchases.manage"))


@router.get("", response_model=list[PurchaseOut], dependencies=[MANAGE])
def list_purchases(
    store_id: int | None = None,
    supplier_id: int | None = None,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(Purchase).options(selectinload(Purchase.items), selectinload(Purchase.payments))
    if store_id is not None:
        query = query.filter(Purchase.store_id == store_id)
    if supplier_id is not None:
        query = query.filter(Purchase.supplier_id == supplier_id)
    return query.order_by(Purchase.id.desc()).limit(limit).all()


@router.get("/{purchase_id}", response_model=PurchaseOut, dependencies=[MANAGE])
def get_purchase(purchase_id: int, db: Session = Depends(get_db)):
    purchase = (
        db.query(Purchase)
        .options(selectinload(Purchase.items), selectinload(Purchase.payments))
        .filter(Purchase.id == purchase_id)
        .first()
    )
    if not purchase:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Purchase not found")
    return purchase


@router.post("", response_model=PurchaseOut, status_code=status.HTTP_201_CREATED, dependencies=[MANAGE])
def record_purchase(payload: PurchaseCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return create_purchase(db, payload, current_user)


@router.post("/{purchase_id}/return", response_model=PurchaseReturnOut, dependencies=[MANAGE])
def return_purchase(
    purchase_id: int,
    payload: PurchaseReturnCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    purchase = db.query(Purchase).options(selectinload(Purchase.items)).filter(Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Purchase not found")
    return_record = return_purchase_items(db, purchase, payload.items, payload.reason, current_user)
    return PurchaseReturnOut(
        id=return_record.id,
        purchase_id=return_record.purchase_id,
        amount=float(return_record.amount),
        reason=return_record.reason,
    )


@router.post("/{purchase_id}/payments", response_model=PurchasePaymentOut, dependencies=[MANAGE])
def add_purchase_payment(
    purchase_id: int,
    payload: PurchasePaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    purchase = (
        db.query(Purchase)
        .options(selectinload(Purchase.payments))
        .filter(Purchase.id == purchase_id)
        .first()
    )
    if not purchase:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Purchase not found")
    return record_purchase_payment(db, purchase, payload, current_user)
