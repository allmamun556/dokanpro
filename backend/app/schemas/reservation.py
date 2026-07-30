from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.models.reservation import ReservationStatus
from app.models.table import TableStatus


class ReservationCreate(BaseModel):
    store_id: int = 1
    party_size: int
    reservation_time: datetime
    guest_name: Optional[str] = None
    guest_phone: Optional[str] = None
    guest_email: Optional[str] = None
    notes: Optional[str] = None


class ReservationUpdate(BaseModel):
    status: Optional[ReservationStatus] = None
    table_id: Optional[int] = None
    party_size: Optional[int] = None
    reservation_time: Optional[datetime] = None
    notes: Optional[str] = None


class ReservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    store_id: int
    customer_id: Optional[int] = None
    guest_name: str
    guest_phone: str
    guest_email: Optional[str] = None
    party_size: int
    reservation_time: datetime
    duration_minutes: int
    table_id: Optional[int] = None
    status: ReservationStatus
    notes: Optional[str] = None
    created_at: datetime


class RestaurantTableOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    store_id: int
    label: str
    capacity: int
    is_active: bool
    status: TableStatus


class RestaurantTableCreate(BaseModel):
    store_id: int = 1
    label: str
    capacity: int


class RestaurantTableUpdate(BaseModel):
    label: Optional[str] = None
    capacity: Optional[int] = None
    is_active: Optional[bool] = None
    status: Optional[TableStatus] = None
