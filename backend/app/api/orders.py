from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_permission
from app.models.user import User
from app.models.notification import NotificationChannel
from app.models.order import Order, OrderItem, OrderStatus, FulfillmentType, FulfillmentStatus
from app.models.business import Business
from app.schemas.order import OrderCreate, OrderOut, RefundCreate, RefundOut
from app.services.audit_service import log_action
from app.services.order_service import create_order, return_order_items, reverse_order_stock
from app.services.invoice_service import generate_invoice_pdf
from app.services import notification_service, ws_manager

router = APIRouter(prefix="/orders", tags=["orders"])

ORDER_OPTIONS = (
    selectinload(Order.items).selectinload(OrderItem.product),
    selectinload(Order.discount),
    selectinload(Order.table),
    selectinload(Order.customer),
)


@router.get("", response_model=list[OrderOut])
def list_orders(
    store_id: int | None = None,
    cashier_id: int | None = None,
    fulfillment_type: FulfillmentType | None = None,
    fulfillment_status: FulfillmentStatus | None = None,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Order).options(*ORDER_OPTIONS)
    if store_id is not None:
        query = query.filter(Order.store_id == store_id)
    if cashier_id is not None:
        query = query.filter(Order.cashier_id == cashier_id)
    if fulfillment_type is not None:
        query = query.filter(Order.fulfillment_type == fulfillment_type)
    if fulfillment_status is not None:
        query = query.filter(Order.fulfillment_status == fulfillment_status)
    return query.order_by(Order.id.desc()).limit(limit).all()


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = (
        db.query(Order)
        .options(*ORDER_OPTIONS)
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return order


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def checkout(payload: OrderCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = create_order(db, payload, current_user)
    return order


@router.post(
    "/{order_id}/refund",
    response_model=RefundOut,
    dependencies=[Depends(require_permission("orders.refund"))],
)
def refund(order_id: int, payload: RefundCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = db.query(Order).options(selectinload(Order.items)).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return return_order_items(db, order, payload.items, payload.reason, current_user)


class FulfillmentStatusUpdate(BaseModel):
    status: FulfillmentStatus


@router.patch(
    "/{order_id}/fulfillment-status",
    response_model=OrderOut,
    dependencies=[Depends(require_permission("orders.fulfill"))],
)
def update_fulfillment_status(
    order_id: int,
    payload: FulfillmentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.query(Order).options(*ORDER_OPTIONS).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    if order.fulfillment_type is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This order is not an online order")

    if order.fulfillment_status == FulfillmentStatus.pending and order.accepted_by_id is None:
        order.accepted_by_id = current_user.id

    if payload.status == FulfillmentStatus.cancelled and order.fulfillment_status != FulfillmentStatus.cancelled:
        # Staff cancelling a paid/accepted order (e.g. kitchen ran out of an
        # ingredient) must release the stock it reserved, same as a failed payment.
        reverse_order_stock(db, order, reference=f"order:{order.id}:staff_cancelled")
        order.status = OrderStatus.voided

    if payload.status == FulfillmentStatus.ready and order.fulfillment_status != FulfillmentStatus.ready:
        if order.fulfillment_type == FulfillmentType.dine_in:
            where = f" for Table {order.table_label}" if order.table_label else ""
        elif order.fulfillment_type == FulfillmentType.delivery:
            where = " — the courier is on the way"
        else:
            where = " for pickup"
        notification_service.send(
            db,
            recipient_email=order.guest_email or (order.customer.email if order.customer else None),
            channel=NotificationChannel.email,
            event_type="order_ready",
            subject=f"Order #{order.id} is ready",
            body=f"Your order #{order.id} is ready{where}.",
            business_id=order.business_id,
        )

    order.fulfillment_status = payload.status
    log_action(db, current_user.id, "update_fulfillment_status", "order", order.id, {"status": payload.status.value}, business_id=current_user.business_id)
    db.commit()
    db.refresh(order)
    ws_manager.broadcast({"type": "order_updated", "order_id": order.id}, business_id=order.business_id)
    return order


@router.get("/{order_id}/invoice")
def get_order_invoice(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = db.query(Order).options(*ORDER_OPTIONS).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    business = db.get(Business, order.business_id)
    pdf_bytes = generate_invoice_pdf(order, business)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="invoice_{order.id}.pdf"'},
    )
