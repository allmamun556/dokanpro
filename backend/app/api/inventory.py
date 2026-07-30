from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_permission
from app.models.user import User
from app.models.product import Product
from app.models.inventory import Inventory, StockMovement, MovementReason
from app.schemas.inventory import StockAdjust, InventoryOut, StockMovementOut
from app.services.audit_service import log_action
from app.services.export_service import export_response

router = APIRouter(prefix="/inventory", tags=["inventory"])

MANAGE = Depends(require_permission("inventory.adjust"))


@router.get("", response_model=list[InventoryOut])
def list_inventory(store_id: int = 1, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (
        db.query(Inventory, Product)
        .join(Product, Product.id == Inventory.product_id)
        .filter(Inventory.store_id == store_id)
        .order_by(Product.name)
        .all()
    )
    return [
        InventoryOut(
            product_id=inv.product_id, store_id=inv.store_id, quantity=inv.quantity,
            reorder_level=inv.reorder_level, product_name=p.name, sku=p.sku,
        )
        for inv, p in rows
    ]


@router.get("/low-stock", response_model=list[InventoryOut])
def low_stock(store_id: int = 1, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (
        db.query(Inventory, Product)
        .join(Product, Product.id == Inventory.product_id)
        .filter(Inventory.store_id == store_id, Inventory.quantity <= Inventory.reorder_level)
        .order_by(Product.name)
        .all()
    )
    return [
        InventoryOut(
            product_id=inv.product_id, store_id=inv.store_id, quantity=inv.quantity,
            reorder_level=inv.reorder_level, product_name=p.name, sku=p.sku,
        )
        for inv, p in rows
    ]


@router.get("/export")
def export_inventory(
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    store_id: int = 1,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = list_inventory(store_id=store_id, db=db, current_user=current_user)
    return export_response(
        format,
        "Inventory Report",
        ["SKU", "Product", "Stock", "Reorder Level"],
        [[r.sku, r.product_name, r.quantity, r.reorder_level] for r in rows],
    )


@router.get("/movements", response_model=list[StockMovementOut])
def list_movements(
    store_id: int = 1,
    product_id: int | None = None,
    reason: MovementReason | None = None,
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(StockMovement, Product, User)
        .join(Product, Product.id == StockMovement.product_id)
        .outerjoin(User, User.id == StockMovement.created_by)
        .filter(StockMovement.store_id == store_id)
    )
    if product_id is not None:
        query = query.filter(StockMovement.product_id == product_id)
    if reason is not None:
        query = query.filter(StockMovement.reason == reason)
    rows = query.order_by(StockMovement.created_at.desc(), StockMovement.id.desc()).limit(limit).all()
    return [
        StockMovementOut(
            id=m.id, product_id=m.product_id, product_name=p.name, sku=p.sku,
            store_id=m.store_id, change_qty=m.change_qty, reason=m.reason,
            reference=m.reference, created_by_name=u.name if u else None,
            created_at=m.created_at,
        )
        for m, p, u in rows
    ]


@router.get("/movements/export")
def export_movements(
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    store_id: int = 1,
    product_id: int | None = None,
    reason: MovementReason | None = None,
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = list_movements(store_id=store_id, product_id=product_id, reason=reason, limit=limit, db=db, current_user=current_user)
    return export_response(
        format,
        "Stock Movement History",
        ["Date", "SKU", "Product", "Change", "Reason", "Reference", "By"],
        [
            [r.created_at.strftime("%Y-%m-%d %H:%M"), r.sku, r.product_name, r.change_qty,
             r.reason.value, r.reference or "", r.created_by_name or ""]
            for r in rows
        ],
    )


@router.post("/adjust", response_model=InventoryOut, dependencies=[MANAGE])
def adjust_stock(payload: StockAdjust, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    inv = db.execute(
        select(Inventory)
        .where(Inventory.product_id == payload.product_id, Inventory.store_id == payload.store_id)
        .with_for_update()
    ).scalar_one_or_none()

    if inv is None:
        inv = Inventory(business_id=current_user.business_id, product_id=payload.product_id, store_id=payload.store_id, quantity=0)
        db.add(inv)
        db.flush()

    new_qty = inv.quantity + payload.change_qty
    if new_qty < 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Resulting stock cannot be negative")

    inv.quantity = new_qty
    db.add(
        StockMovement(
            business_id=current_user.business_id,
            product_id=payload.product_id,
            store_id=payload.store_id,
            change_qty=payload.change_qty,
            reason=payload.reason,
            reference=payload.reference,
            created_by=current_user.id,
        )
    )
    log_action(db, current_user.id, "stock_adjust", "product", payload.product_id, {"change_qty": payload.change_qty}, business_id=current_user.business_id)
    db.commit()
    db.refresh(inv)

    product = db.get(Product, payload.product_id)
    return InventoryOut(
        product_id=inv.product_id, store_id=inv.store_id, quantity=inv.quantity,
        reorder_level=inv.reorder_level, product_name=product.name, sku=product.sku,
    )
