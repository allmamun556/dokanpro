from typing import Optional

from sqlalchemy import String, Numeric, Date, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    category: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    expense_date: Mapped[Date] = mapped_column(Date)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
