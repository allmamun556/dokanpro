from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.inventory import Inventory, StockMovement, MovementReason
from app.models.purchase import Purchase, PurchaseItem, PurchaseReturn, PurchaseReturnItem, PurchasePayment, PurchaseStatus
from app.models.user import User
from app.schemas.purchase import PurchaseCreate, PurchaseReturnItemIn, PurchasePaymentCreate
from app.services.audit_service import log_action


def _q2(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def create_purchase(db: Session, purchase_in: PurchaseCreate, user: User) -> Purchase:
    """
    Records stock received from a supplier: increases inventory for each line
    and logs a StockMovement, all in one transaction (mirrors create_order).
    """
    if not purchase_in.items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Purchase must contain at least one item")

    try:
        subtotal = Decimal("0")
        tax_total = Decimal("0")
        purchase_items: list[PurchaseItem] = []

        for line in purchase_in.items:
            if line.qty <= 0:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Quantity must be positive")

            product = db.get(Product, line.product_id)
            if product is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"Product {line.product_id} not found")

            unit_cost = _q2(line.unit_cost)
            line_subtotal = _q2(unit_cost * line.qty)
            line_tax = _q2(line_subtotal * (Decimal(line.tax_rate) / Decimal(100)))
            line_total = _q2(line_subtotal + line_tax)

            subtotal += line_subtotal
            tax_total += line_tax

            inv = db.execute(
                select(Inventory)
                .where(Inventory.product_id == line.product_id, Inventory.store_id == purchase_in.store_id)
                .with_for_update()
            ).scalar_one_or_none()
            if inv is None:
                inv = Inventory(business_id=user.business_id, product_id=line.product_id, store_id=purchase_in.store_id, quantity=0)
                db.add(inv)
                db.flush()
            inv.quantity += line.qty

            db.add(
                StockMovement(
                    business_id=user.business_id,
                    product_id=product.id,
                    store_id=purchase_in.store_id,
                    change_qty=line.qty,
                    reason=MovementReason.purchase,
                    created_by=user.id,
                )
            )

            purchase_items.append(
                PurchaseItem(
                    business_id=user.business_id,
                    product_id=product.id,
                    qty=line.qty,
                    unit_cost=unit_cost,
                    tax_amount=line_tax,
                    line_total=line_total,
                )
            )

        discount_total = _q2(purchase_in.discount_total)
        total = _q2(subtotal + tax_total - discount_total)

        purchase = Purchase(
            business_id=user.business_id,
            store_id=purchase_in.store_id,
            supplier_id=purchase_in.supplier_id,
            created_by=user.id,
            invoice_number=purchase_in.invoice_number,
            status=PurchaseStatus.completed,
            subtotal=subtotal,
            tax_total=tax_total,
            discount_total=discount_total,
            total=total,
            items=purchase_items,
        )
        db.add(purchase)
        db.flush()

        log_action(db, user.id, "create", "purchase", purchase.id, {"total": str(total)}, business_id=user.business_id)

        db.commit()
        db.refresh(purchase)
        return purchase

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


def return_purchase_items(
    db: Session, purchase: Purchase, items_in: list[PurchaseReturnItemIn], reason: str, user: User
) -> PurchaseReturn:
    """
    Returns specific quantities of purchased items back to the supplier:
    removes the stock and records the return, restricted to what's left to return.
    """
    if not items_in:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Return must contain at least one item")

    try:
        total_amount = Decimal("0")
        return_items: list[PurchaseReturnItem] = []

        for req in items_in:
            if req.qty <= 0:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Quantity must be positive")

            purchase_item = next((pi for pi in purchase.items if pi.product_id == req.product_id), None)
            if purchase_item is None:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Product {req.product_id} was not part of this purchase")

            remaining = purchase_item.qty - purchase_item.returned_qty
            if req.qty > remaining:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Cannot return {req.qty} of product {req.product_id}: only {remaining} left to return",
                )

            inv = db.execute(
                select(Inventory)
                .where(Inventory.product_id == req.product_id, Inventory.store_id == purchase.store_id)
                .with_for_update()
            ).scalar_one_or_none()
            if inv is None or inv.quantity < req.qty:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Not enough stock on hand for product {req.product_id} to return to supplier",
                )
            inv.quantity -= req.qty

            db.add(
                StockMovement(
                    business_id=user.business_id,
                    product_id=req.product_id,
                    store_id=purchase.store_id,
                    change_qty=-req.qty,
                    reason=MovementReason.purchase_return,
                    created_by=user.id,
                    reference=f"purchase:{purchase.id}",
                )
            )

            unit_tax = purchase_item.tax_amount / purchase_item.qty if purchase_item.qty else Decimal("0")
            line_total = _q2((purchase_item.unit_cost + unit_tax) * req.qty)
            total_amount += line_total

            purchase_item.returned_qty += req.qty
            return_items.append(PurchaseReturnItem(business_id=user.business_id, product_id=req.product_id, qty=req.qty, line_total=line_total))

        all_returned = all(pi.returned_qty >= pi.qty for pi in purchase.items)
        any_returned = any(pi.returned_qty > 0 for pi in purchase.items)
        purchase.status = PurchaseStatus.returned if all_returned else (
            PurchaseStatus.partially_returned if any_returned else PurchaseStatus.completed
        )

        purchase_return = PurchaseReturn(
            business_id=user.business_id,
            purchase_id=purchase.id,
            reason=reason,
            amount=_q2(total_amount),
            processed_by=user.id,
            items=return_items,
        )
        db.add(purchase_return)
        db.flush()

        log_action(db, user.id, "return", "purchase", purchase.id, {"amount": str(_q2(total_amount))}, business_id=user.business_id)

        db.commit()
        db.refresh(purchase_return)
        return purchase_return

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


def record_purchase_payment(db: Session, purchase: Purchase, payload: PurchasePaymentCreate, user: User) -> PurchasePayment:
    """Records a payment against a purchase, never exceeding what's still due."""
    amount = _q2(payload.amount)
    if amount <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Amount must be positive")

    due = _q2(purchase.due_amount)
    if amount > due:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Payment of {amount} exceeds the remaining due amount ({due})",
        )

    try:
        payment = PurchasePayment(
            business_id=user.business_id,
            purchase_id=purchase.id,
            amount=amount,
            payment_date=payload.payment_date,
            method=payload.method,
            note=payload.note,
            created_by=user.id,
        )
        db.add(payment)
        db.flush()

        log_action(db, user.id, "payment", "purchase", purchase.id, {"amount": str(amount)}, business_id=user.business_id)

        db.commit()
        db.refresh(payment)
        return payment

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
