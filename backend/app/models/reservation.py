import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Text, ForeignKey, Enum as SAEnum, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ReservationStatus(str, enum.Enum):
    requested = "requested"
    confirmed = "confirmed"
    seated = "seated"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id"), nullable=True)

    guest_name: Mapped[str] = mapped_column(String(150))
    guest_phone: Mapped[str] = mapped_column(String(30))
    guest_email: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    party_size: Mapped[int] = mapped_column(Integer)
    reservation_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int] = mapped_column(Integer, default=90)

    table_id: Mapped[Optional[int]] = mapped_column(ForeignKey("restaurant_tables.id"), nullable=True)
    status: Mapped[ReservationStatus] = mapped_column(SAEnum(ReservationStatus), default=ReservationStatus.requested)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    customer: Mapped[Optional["Customer"]] = relationship()
    table: Mapped[Optional["RestaurantTable"]] = relationship()
