import enum
from typing import Optional

from sqlalchemy import String, Numeric, Boolean, DateTime, Enum as SAEnum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DiscountType(str, enum.Enum):
    percentage = "percentage"
    fixed = "fixed"


class Discount(Base):
    __tablename__ = "discounts"
    __table_args__ = (UniqueConstraint("business_id", "code", name="uq_discounts_business_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(150))
    type: Mapped[DiscountType] = mapped_column(SAEnum(DiscountType))
    value: Mapped[float] = mapped_column(Numeric(10, 2))
    min_subtotal: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    starts_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
