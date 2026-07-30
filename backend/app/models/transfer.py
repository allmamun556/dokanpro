from typing import Optional

from sqlalchemy import String, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StockTransfer(Base):
    __tablename__ = "stock_transfers"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    from_store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    to_store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    qty: Mapped[int] = mapped_column(Integer)
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
