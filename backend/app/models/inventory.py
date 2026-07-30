import enum
from typing import Optional

from sqlalchemy import Integer, ForeignKey, Enum as SAEnum, DateTime, func, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MovementReason(str, enum.Enum):
    sale = "sale"
    restock = "restock"
    adjustment = "adjustment"
    return_ = "return"
    refund = "refund"
    purchase = "purchase"
    purchase_return = "purchase_return"
    transfer_in = "transfer_in"
    transfer_out = "transfer_out"


class Inventory(Base):
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    reorder_level: Mapped[int] = mapped_column(Integer, default=5)

    product: Mapped["Product"] = relationship()


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    change_qty: Mapped[int] = mapped_column(Integer)
    reason: Mapped[MovementReason] = mapped_column(SAEnum(MovementReason))
    reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
