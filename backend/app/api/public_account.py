from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.core.deps import get_current_customer
from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.models.reservation import Reservation
from app.models.business import Business
from app.schemas.order import OrderOut
from app.schemas.reservation import ReservationOut
from app.services.invoice_service import generate_invoice_pdf

router = APIRouter(prefix="/account", tags=["public-account"])

ORDER_OPTIONS = (
    selectinload(Order.items).selectinload(OrderItem.product),
    selectinload(Order.table),
    selectinload(Order.customer),
)


@router.get("/orders", response_model=list[OrderOut])
def list_my_orders(db: Session = Depends(get_db), customer: Customer = Depends(get_current_customer)):
    return (
        db.query(Order)
        .options(*ORDER_OPTIONS)
        .filter(Order.customer_id == customer.id)
        .order_by(Order.created_at.desc())
        .all()
    )


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_my_order(order_id: int, db: Session = Depends(get_db), customer: Customer = Depends(get_current_customer)):
    order = db.query(Order).options(*ORDER_OPTIONS).filter(Order.id == order_id).first()
    if order is None or order.customer_id != customer.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return order


@router.get("/orders/{order_id}/invoice")
def get_my_order_invoice(order_id: int, db: Session = Depends(get_db), customer: Customer = Depends(get_current_customer)):
    order = db.query(Order).options(*ORDER_OPTIONS).filter(Order.id == order_id).first()
    if order is None or order.customer_id != customer.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    business = db.get(Business, order.business_id)
    pdf_bytes = generate_invoice_pdf(order, business)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="invoice_{order.id}.pdf"'},
    )


@router.get("/reservations", response_model=list[ReservationOut])
def list_my_reservations(db: Session = Depends(get_db), customer: Customer = Depends(get_current_customer)):
    return (
        db.query(Reservation)
        .filter(Reservation.customer_id == customer.id)
        .order_by(Reservation.reservation_time.desc())
        .all()
    )
