import enum
from typing import Optional

from sqlalchemy import String, Integer, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TableStatus(str, enum.Enum):
    free = "free"
    occupied = "occupied"
    reserved = "reserved"


class RestaurantTable(Base):
    __tablename__ = "restaurant_tables"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    label: Mapped[str] = mapped_column(String(50))
    capacity: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[TableStatus] = mapped_column(SAEnum(TableStatus), default=TableStatus.free)
