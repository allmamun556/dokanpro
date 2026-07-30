from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.notification import NotificationChannel
from app.models.reservation import Reservation, ReservationStatus
from app.schemas.reservation import ReservationCreate
from app.services import notification_service


def create_reservation(
    db: Session, payload: ReservationCreate, customer: Optional[Customer], business_id: int
) -> Reservation:
    if payload.party_size <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Party size must be positive")

    guest_name = customer.name if customer else payload.guest_name
    guest_phone = customer.phone if customer else payload.guest_phone
    guest_email = customer.email if customer else payload.guest_email

    if not guest_name or not guest_phone:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Name and phone number are required")

    reservation = Reservation(
        business_id=business_id,
        store_id=payload.store_id,
        customer_id=customer.id if customer else None,
        guest_name=guest_name,
        guest_phone=guest_phone,
        guest_email=guest_email,
        party_size=payload.party_size,
        reservation_time=payload.reservation_time,
        status=ReservationStatus.requested,
        notes=payload.notes,
    )
    db.add(reservation)
    db.flush()

    notification_service.send(
        db,
        recipient_email=guest_email,
        recipient_phone=guest_phone,
        channel=NotificationChannel.email,
        event_type="reservation_created",
        subject="Reservation received",
        body=(
            f"Hi {guest_name}, we've received your reservation request for "
            f"{payload.party_size} on {payload.reservation_time}. We'll confirm shortly."
        ),
        business_id=business_id,
    )

    db.commit()
    db.refresh(reservation)
    return reservation
