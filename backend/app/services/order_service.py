from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.product import Product
from app.models.inventory import Inventory, StockMovement, MovementReason
from app.models.order import (
    Order, OrderItem, Refund, RefundItem, OrderStatus, PaymentMethod, FulfillmentType, FulfillmentStatus,
)
from app.models.user import User
from app.schemas.order import OrderCreate, OrderItemIn, PublicOrderCreate, RefundItemIn
from app.services.audit_service import log_action
from app.services.discount_service import get_active_discount, compute_discount_amount
from app.services import ws_manager


def _q2(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _credit_loyalty_points(db: Session, customer_id: Optional[int], total: Decimal) -> None:
    """1 point per whole €1 spent. No accrual for guest checkout or walk-in sales with no customer attached."""
    if customer_id is None:
        return
    customer = db.get(Customer, customer_id)
    if customer is not None:
        customer.loyalty_points += int(total)


def reverse_order_stock(db: Session, order: Order, reference: str) -> None:
    """
    Restores the stock an order had reserved, and reverses any loyalty points
    earned/redeemed on it. Used both when a Stripe payment never completes and
    when staff cancel an online order after the fact (e.g. the kitchen ran out
    of an ingredient) — either way, stock/points from order-creation time must
    not stay silently applied forever.
    """
    for item in order.items:
        inv = db.execute(
            select(Inventory)
            .where(Inventory.product_id == item.product_id, Inventory.store_id == order.store_id)
            .with_for_update()
        ).scalar_one_or_none()
        if inv is not None:
            inv.quantity += item.qty
            db.add(
                StockMovement(
                    business_id=order.business_id,
                    product_id=item.product_id,
                    store_id=order.store_id,
                    change_qty=item.qty,
                    reason=MovementReason.adjustment,
                    reference=reference,
                )
            )

    if order.customer_id is not None:
        customer = db.get(Customer, order.customer_id)
        if customer is not None:
            # Give back points earned, minus any that were redeemed on this order.
            customer.loyalty_points = max(0, customer.loyalty_points - int(order.total))
            if order.loyalty_points_redeemed:
                customer.loyalty_points += order.loyalty_points_redeemed


def _reserve_stock_and_price_items(
    db: Session, items_in: list[OrderItemIn], store_id: int, created_by: Optional[int], business_id: int
) -> tuple[list[OrderItem], Decimal, Decimal]:
    """
    Locks each product's inventory row (SELECT ... FOR UPDATE), validates stock,
    deducts it, records a StockMovement per line, and prices lines server-side
    (never trusts a client-sent price). Shared by staff POS checkout and public
    online checkout so both go through the exact same stock/pricing rules.
    """
    subtotal = Decimal("0")
    tax_total = Decimal("0")
    order_items: list[OrderItem] = []

    for line in items_in:
        if line.qty <= 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Quantity must be positive")

        product = db.get(Product, line.product_id)
        if product is None or not product.is_active:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Product {line.product_id} not found")

        # Lock the inventory row for this product/store to prevent overselling
        inv = db.execute(
            select(Inventory)
            .where(
                Inventory.product_id == line.product_id,
                Inventory.store_id == store_id,
            )
            .with_for_update()
        ).scalar_one_or_none()

        if inv is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"No inventory record for product {product.name} at this store",
            )
        if inv.quantity < line.qty:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Insufficient stock for {product.name}: have {inv.quantity}, requested {line.qty}",
            )

        unit_price = _q2(product.price)
        line_discount = _q2(line.discount_amount)
        line_subtotal = _q2(unit_price * line.qty) - line_discount
        line_tax = _q2(line_subtotal * (Decimal(product.tax_rate) / Decimal(100)))
        line_total = _q2(line_subtotal + line_tax)

        subtotal += _q2(unit_price * line.qty)
        tax_total += line_tax

        # Deduct stock
        inv.quantity -= line.qty
        db.add(
            StockMovement(
                business_id=business_id,
                product_id=product.id,
                store_id=store_id,
                change_qty=-line.qty,
                reason=MovementReason.sale,
                created_by=created_by,
            )
        )

        order_items.append(
            OrderItem(
                business_id=business_id,
                product_id=product.id,
                qty=line.qty,
                unit_price=unit_price,
                tax_amount=line_tax,
                discount_amount=line_discount,
                line_total=line_total,
                special_instructions=line.special_instructions,
            )
        )

    return order_items, subtotal, tax_total


def _apply_discount(db: Session, discount_code: Optional[str], subtotal: Decimal, tax_total: Decimal):
    if not discount_code:
        return None, Decimal("0")
    discount = get_active_discount(db, discount_code, subtotal)
    discount_total = compute_discount_amount(discount, subtotal, cap=subtotal + tax_total)
    return discount, discount_total


LOYALTY_REDEEM_POINTS = 100
LOYALTY_REDEEM_VALUE = Decimal("5")


def _apply_loyalty_redemption(
    customer: Optional[Customer], redeem: bool, remaining: Decimal
) -> tuple[int, Decimal]:
    """Flat-tier redemption: 100 points = €5 off, capped at what's left after any discount code."""
    if not redeem:
        return 0, Decimal("0")
    if customer is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Log in to redeem loyalty points")
    if customer.loyalty_points < LOYALTY_REDEEM_POINTS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"You need at least {LOYALTY_REDEEM_POINTS} points to redeem")
    customer.loyalty_points -= LOYALTY_REDEEM_POINTS
    amount = min(LOYALTY_REDEEM_VALUE, max(Decimal("0"), remaining))
    return LOYALTY_REDEEM_POINTS, amount


def create_order(db: Session, order_in: OrderCreate, cashier: User) -> Order:
    """
    Creates a staff POS order atomically. All within a single DB transaction
    so a crash or a concurrent sale can never leave inventory in an
    inconsistent state.
    """
    if not order_in.items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Order must contain at least one item")

    try:
        order_items, subtotal, tax_total = _reserve_stock_and_price_items(
            db, order_in.items, order_in.store_id, created_by=cashier.id, business_id=cashier.business_id
        )
        discount, discount_total = _apply_discount(db, order_in.discount_code, subtotal, tax_total)

        total = _q2(subtotal + tax_total - discount_total)

        tendered = _q2(order_in.tendered) if order_in.tendered is not None else None
        change_given = None
        if order_in.payment_method == PaymentMethod.cash:
            if tendered is None or tendered < total:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST, "Cash tendered must be provided and >= total"
                )
            change_given = _q2(tendered - total)

        order = Order(
            business_id=cashier.business_id,
            store_id=order_in.store_id,
            cashier_id=cashier.id,
            customer_id=order_in.customer_id,
            discount_id=discount.id if discount else None,
            status=OrderStatus.completed,
            subtotal=subtotal,
            tax_total=tax_total,
            discount_total=discount_total,
            total=total,
            payment_method=order_in.payment_method,
            payment_reference=order_in.payment_reference,
            tendered=tendered,
            change_given=change_given,
            table_id=order_in.table_id,
            items=order_items,
        )
        db.add(order)
        db.flush()

        _credit_loyalty_points(db, order.customer_id, total)
        log_action(db, cashier.id, "checkout", "order", order.id, {"total": str(total)}, business_id=cashier.business_id)

        db.commit()
        db.refresh(order)
        return order

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


def create_public_order(
    db: Session, order_in: PublicOrderCreate, customer: Optional[Customer], business_id: int
) -> Order:
    """
    Creates an online (pickup/delivery) order. No cashier is involved yet —
    fulfillment_status starts at 'pending' until the kitchen/staff acknowledge
    it via the admin order queue. Payment is via Stripe, not a cash drawer, so
    stock is reserved immediately (before the Stripe redirect) to avoid
    overselling; if payment fails/expires the caller must reverse the
    StockMovements this creates (see public_checkout_service).
    """
    if not order_in.items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Order must contain at least one item")

    if order_in.fulfillment_type == FulfillmentType.dine_in:
        # The table is the identifier for a dine-in order — no guest name/phone
        # needed, unlike pickup/delivery where staff need a way to reach the customer.
        if not order_in.table_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "table_id is required for dine-in orders")
    elif customer is None and not (order_in.guest_name and order_in.guest_phone):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Guest checkout requires a name and phone number")

    if order_in.fulfillment_type == FulfillmentType.delivery and not order_in.delivery_address:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Delivery address is required for delivery orders")

    try:
        order_items, subtotal, tax_total = _reserve_stock_and_price_items(
            db, order_in.items, order_in.store_id, created_by=None, business_id=business_id
        )
        discount, discount_total = _apply_discount(db, order_in.discount_code, subtotal, tax_total)

        remaining_after_discount = subtotal + tax_total - discount_total
        points_redeemed, loyalty_amount = _apply_loyalty_redemption(
            customer, order_in.redeem_loyalty_points, remaining_after_discount
        )

        total = _q2(remaining_after_discount - loyalty_amount)

        order = Order(
            business_id=business_id,
            store_id=order_in.store_id,
            cashier_id=None,
            customer_id=customer.id if customer else None,
            guest_name=None if customer else order_in.guest_name,
            guest_phone=None if customer else order_in.guest_phone,
            guest_email=None if customer else order_in.guest_email,
            discount_id=discount.id if discount else None,
            status=OrderStatus.completed,
            subtotal=subtotal,
            tax_total=tax_total,
            discount_total=discount_total,
            total=total,
            loyalty_points_redeemed=points_redeemed or None,
            payment_method=PaymentMethod.online,
            fulfillment_type=order_in.fulfillment_type,
            fulfillment_status=FulfillmentStatus.pending,
            delivery_address=order_in.delivery_address,
            requested_time=order_in.requested_time,
            table_id=order_in.table_id,
            items=order_items,
        )
        db.add(order)
        db.flush()

        _credit_loyalty_points(db, order.customer_id, total)
        log_action(
            db, customer.id if customer else None, "public_checkout", "order", order.id, {"total": str(total)},
            business_id=business_id,
        )

        db.commit()
        db.refresh(order)
        ws_manager.broadcast({"type": "order_updated", "order_id": order.id}, business_id=order.business_id)
        return order

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


def return_order_items(
    db: Session, order: Order, items_in: list[RefundItemIn], reason: str, processed_by: User
) -> Refund:
    """
    Returns specific quantities of specific order items: restocks inventory
    precisely for what's returned and computes the refund amount from the
    order's own recorded prices (never trusts a client-sent amount).
    """
    if not items_in:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Return must contain at least one item")

    try:
        total_amount = Decimal("0")
        refund_items: list[RefundItem] = []

        for req in items_in:
            if req.qty <= 0:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Quantity must be positive")

            order_item = next((oi for oi in order.items if oi.product_id == req.product_id), None)
            if order_item is None:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Product {req.product_id} was not part of this order")

            remaining = order_item.qty - order_item.returned_qty
            if req.qty > remaining:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Cannot return {req.qty} of product {req.product_id}: only {remaining} left to return",
                )

            inv = db.execute(
                select(Inventory)
                .where(Inventory.product_id == req.product_id, Inventory.store_id == order.store_id)
                .with_for_update()
            ).scalar_one_or_none()
            if inv is not None:
                inv.quantity += req.qty
                db.add(
                    StockMovement(
                        business_id=order.business_id,
                        product_id=req.product_id,
                        store_id=order.store_id,
                        change_qty=req.qty,
                        reason=MovementReason.refund,
                        created_by=processed_by.id,
                        reference=f"order:{order.id}",
                    )
                )

            unit_value = order_item.line_total / order_item.qty if order_item.qty else Decimal("0")
            line_total = _q2(unit_value * req.qty)
            total_amount += line_total

            order_item.returned_qty += req.qty
            refund_items.append(RefundItem(business_id=order.business_id, product_id=req.product_id, qty=req.qty, line_total=line_total))

        all_returned = all(oi.returned_qty >= oi.qty for oi in order.items)
        any_returned = any(oi.returned_qty > 0 for oi in order.items)
        order.status = OrderStatus.refunded if all_returned else (
            OrderStatus.partially_refunded if any_returned else order.status
        )

        refund = Refund(
            business_id=order.business_id,
            order_id=order.id,
            reason=reason,
            amount=_q2(total_amount),
            processed_by=processed_by.id,
            items=refund_items,
        )
        db.add(refund)
        db.flush()

        log_action(db, processed_by.id, "return", "order", order.id, {"amount": str(_q2(total_amount))}, business_id=processed_by.business_id)

        db.commit()
        db.refresh(refund)
        return refund

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
