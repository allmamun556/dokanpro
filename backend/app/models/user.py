import enum
from typing import Optional

from sqlalchemy import String, Boolean, Numeric, Date, Enum as SAEnum, DateTime, func, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RoleEnum(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    cashier = "cashier"
    waiter = "waiter"
    chef = "chef"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("business_id", "email", name="uq_users_business_email"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(150), index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[RoleEnum] = mapped_column(SAEnum(RoleEnum), default=RoleEnum.cashier)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    hire_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    salary: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    permission_overrides: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
