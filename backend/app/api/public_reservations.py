from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_customer_optional, require_tenant
from app.core.rate_limit import limiter
from app.models.customer import Customer
from app.models.reservation import Reservation
from app.schemas.reservation import ReservationCreate, ReservationOut
from app.services import reservation_service

router = APIRouter(prefix="/reservations", tags=["public-reservations"])


@router.post("", response_model=ReservationOut)
@limiter.limit("10/minute")
def create_reservation(
    payload: ReservationCreate,
    request: Request,
    db: Session = Depends(get_db),
    customer: Optional[Customer] = Depends(get_current_customer_optional),
):
    if request.state.business_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unable to determine which restaurant this reservation belongs to")
    return reservation_service.create_reservation(db, payload, customer, request.state.business_id)


@router.get("/{reservation_id}", response_model=ReservationOut, dependencies=[Depends(require_tenant)])
def get_reservation(
    reservation_id: int,
    email: Optional[str] = None,
    db: Session = Depends(get_db),
    customer: Optional[Customer] = Depends(get_current_customer_optional),
):
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservation not found")

    owns_as_customer = customer is not None and reservation.customer_id == customer.id
    owns_as_guest = (
        email is not None
        and reservation.guest_email is not None
        and email.lower() == reservation.guest_email.lower()
    )
    if not (owns_as_customer or owns_as_guest):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservation not found")

    return reservation
