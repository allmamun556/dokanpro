from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_permission
from app.models.notification import NotificationChannel
from app.models.reservation import Reservation, ReservationStatus
from app.models.table import RestaurantTable
from app.schemas.reservation import (
    ReservationOut, ReservationUpdate, RestaurantTableOut, RestaurantTableCreate, RestaurantTableUpdate,
)
from app.services.audit_service import log_action
from app.services import notification_service

router = APIRouter(tags=["reservations"])

MANAGE = Depends(require_permission("reservations.manage"))
TABLES_MANAGE = Depends(require_permission("tables.manage"))


@router.get("/reservations", response_model=list[ReservationOut], dependencies=[Depends(get_current_user)])
def list_reservations(
    date_filter: date | None = None,
    status_filter: ReservationStatus | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Reservation)
    if date_filter is not None:
        start = datetime.combine(date_filter, time.min, tzinfo=timezone.utc)
        end = datetime.combine(date_filter, time.max, tzinfo=timezone.utc)
        query = query.filter(Reservation.reservation_time >= start, Reservation.reservation_time <= end)
    if status_filter is not None:
        query = query.filter(Reservation.status == status_filter)
    return query.order_by(Reservation.reservation_time).all()


@router.patch("/reservations/{reservation_id}", response_model=ReservationOut, dependencies=[MANAGE])
def update_reservation(
    reservation_id: int,
    payload: ReservationUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    reservation = db.get(Reservation, reservation_id)
    if not reservation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservation not found")

    updates = payload.model_dump(exclude_unset=True)
    newly_confirmed = updates.get("status") == ReservationStatus.confirmed and reservation.status != ReservationStatus.confirmed
    for field, value in updates.items():
        setattr(reservation, field, value)

    if newly_confirmed:
        notification_service.send(
            db,
            recipient_email=reservation.guest_email,
            recipient_phone=reservation.guest_phone,
            channel=NotificationChannel.email,
            event_type="reservation_confirmed",
            subject="Reservation confirmed",
            body=(
                f"Your table for {reservation.party_size} on {reservation.reservation_time} "
                f"is confirmed. See you soon!"
            ),
            business_id=reservation.business_id,
        )

    log_action(db, current_user.id, "update", "reservation", reservation.id, business_id=current_user.business_id)
    db.commit()
    db.refresh(reservation)
    return reservation


@router.get("/reservation-tables", response_model=list[RestaurantTableOut], dependencies=[Depends(get_current_user)])
def list_tables(db: Session = Depends(get_db)):
    return db.query(RestaurantTable).order_by(RestaurantTable.label).all()


@router.post("/reservation-tables", response_model=RestaurantTableOut, dependencies=[MANAGE])
def create_table(payload: RestaurantTableCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    table = RestaurantTable(business_id=current_user.business_id, **payload.model_dump())
    db.add(table)
    db.commit()
    db.refresh(table)
    return table


@router.patch("/reservation-tables/{table_id}", response_model=RestaurantTableOut, dependencies=[TABLES_MANAGE])
def update_table(
    table_id: int,
    payload: RestaurantTableUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    table = db.get(RestaurantTable, table_id)
    if not table:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Table not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(table, field, value)
    log_action(db, current_user.id, "update", "table", table.id, business_id=current_user.business_id)
    db.commit()
    db.refresh(table)
    return table
