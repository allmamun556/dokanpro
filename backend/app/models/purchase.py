import enum
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import String, Numeric, Integer, Date, ForeignKey, Enum as SAEnum, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.order import PaymentMethod


class PurchaseStatus(str, enum.Enum):
    completed = "completed"
    returned = "returned"
    partially_returned = "partially_returned"


class Purchase(Base):
    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    supplier_id: Mapped[Optional[int]] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    invoice_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[PurchaseStatus] = mapped_column(SAEnum(PurchaseStatus), default=PurchaseStatus.completed)
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2))
    tax_total: Mapped[float] = mapped_column(Numeric(10, 2))
    discount_total: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    total: Mapped[float] = mapped_column(Numeric(10, 2))
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[List["PurchaseItem"]] = relationship(back_populates="purchase", cascade="all, delete-orphan")
    payments: Mapped[List["PurchasePayment"]] = relationship(back_populates="purchase", cascade="all, delete-orphan")
    supplier: Mapped[Optional["Supplier"]] = relationship()

    @property
    def paid_amount(self) -> Decimal:
        return sum((p.amount for p in self.payments), Decimal("0"))

    @property
    def due_amount(self) -> Decimal:
        return self.total - self.paid_amount


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchases.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    qty: Mapped[int] = mapped_column(Integer)
    unit_cost: Mapped[float] = mapped_column(Numeric(10, 2))
    tax_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    line_total: Mapped[float] = mapped_column(Numeric(10, 2))
    returned_qty: Mapped[int] = mapped_column(Integer, default=0)

    purchase: Mapped["Purchase"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()


class PurchasePayment(Base):
    __tablename__ = "purchase_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchases.id"))
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    payment_date: Mapped[Date] = mapped_column(Date)
    method: Mapped[PaymentMethod] = mapped_column(SAEnum(PaymentMethod))
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    purchase: Mapped["Purchase"] = relationship(back_populates="payments")


class PurchaseReturn(Base):
    __tablename__ = "purchase_returns"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchases.id"))
    reason: Mapped[str] = mapped_column(String(255))
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    processed_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[List["PurchaseReturnItem"]] = relationship(back_populates="purchase_return", cascade="all, delete-orphan")


class PurchaseReturnItem(Base):
    __tablename__ = "purchase_return_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    purchase_return_id: Mapped[int] = mapped_column(ForeignKey("purchase_returns.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    qty: Mapped[int] = mapped_column(Integer)
    line_total: Mapped[float] = mapped_column(Numeric(10, 2))

    purchase_return: Mapped["PurchaseReturn"] = relationship(back_populates="items")
