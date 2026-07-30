from typing import Optional

from sqlalchemy import String, ForeignKey, DateTime, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class HeldSale(Base):
    """A parked cart, saved before checkout so a cashier can serve another customer and resume later."""
    __tablename__ = "held_sales"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id"), nullable=True)
    items: Mapped[list] = mapped_column(JSON)
    discount_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    created_by_user: Mapped["User"] = relationship()
