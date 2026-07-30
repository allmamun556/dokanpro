from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_permission
from app.models.supplier import Supplier
from app.models.purchase import Purchase, PurchasePayment
from app.schemas.supplier import SupplierCreate, SupplierUpdate, SupplierOut

router = APIRouter(prefix="/suppliers", tags=["suppliers"])

MANAGE = Depends(require_permission("suppliers.manage"))


def _due_by_supplier(db: Session) -> dict:
    totals = dict(
        db.query(Purchase.supplier_id, func.coalesce(func.sum(Purchase.total), 0))
        .filter(Purchase.supplier_id.isnot(None))
        .group_by(Purchase.supplier_id)
        .all()
    )
    paid = dict(
        db.query(Purchase.supplier_id, func.coalesce(func.sum(PurchasePayment.amount), 0))
        .join(PurchasePayment, PurchasePayment.purchase_id == Purchase.id)
        .filter(Purchase.supplier_id.isnot(None))
        .group_by(Purchase.supplier_id)
        .all()
    )
    return {sid: float(total) - float(paid.get(sid, 0)) for sid, total in totals.items()}


def _to_out(supplier: Supplier, due_map: dict) -> SupplierOut:
    return SupplierOut(
        id=supplier.id,
        name=supplier.name,
        phone=supplier.phone,
        email=supplier.email,
        address=supplier.address,
        total_due=due_map.get(supplier.id, 0.0),
    )


@router.get("", response_model=list[SupplierOut])
def list_suppliers(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    suppliers = db.query(Supplier).order_by(Supplier.name).all()
    due_map = _due_by_supplier(db)
    return [_to_out(s, due_map) for s in suppliers]


@router.post("", response_model=SupplierOut, status_code=status.HTTP_201_CREATED, dependencies=[MANAGE])
def create_supplier(payload: SupplierCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    supplier = Supplier(business_id=current_user.business_id, **payload.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return _to_out(supplier, {})


@router.patch("/{supplier_id}", response_model=SupplierOut, dependencies=[MANAGE])
def update_supplier(supplier_id: int, payload: SupplierUpdate, db: Session = Depends(get_db)):
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplier not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(supplier, field, value)
    db.commit()
    db.refresh(supplier)
    return _to_out(supplier, _due_by_supplier(db))


@router.get("/{supplier_id}", response_model=SupplierOut)
def get_supplier(supplier_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplier not found")
    return _to_out(supplier, _due_by_supplier(db))
