from typing import Optional

from sqlalchemy import String, Integer, Boolean, Index, text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        # Only login-capable customers (password_hash set) need a unique email
        # (per business — the same person may have accounts at two different
        # restaurants) — staff-entered walk-in CRM records may share/omit emails.
        Index(
            "ix_customers_email_login_unique",
            "business_id",
            "email",
            unique=True,
            postgresql_where=text("password_hash IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    loyalty_points: Mapped[int] = mapped_column(Integer, default=0)

    # Customer self-service login (Phase 1 restaurant platform). Null password_hash
    # means this row is a staff-created CRM record with no login capability.
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
