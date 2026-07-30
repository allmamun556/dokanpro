import enum
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Numeric, Integer, Text, ForeignKey, Enum as SAEnum, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrderStatus(str, enum.Enum):
    completed = "completed"
    refunded = "refunded"
    partially_refunded = "partially_refunded"
    voided = "voided"


class PaymentMethod(str, enum.Enum):
    cash = "cash"
    card = "card"
    mobile = "mobile"
    bkash = "bkash"
    nagad = "nagad"
    rocket = "rocket"
    online = "online"
    other = "other"


class FulfillmentType(str, enum.Enum):
    pickup = "pickup"
    delivery = "delivery"
    dine_in = "dine_in"


class FulfillmentStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    preparing = "preparing"
    ready = "ready"
    completed = "completed"
    cancelled = "cancelled"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    cashier_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id"), nullable=True)
    discount_id: Mapped[Optional[int]] = mapped_column(ForeignKey("discounts.id"), nullable=True)
    status: Mapped[OrderStatus] = mapped_column(SAEnum(OrderStatus), default=OrderStatus.completed)
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2))
    tax_total: Mapped[float] = mapped_column(Numeric(10, 2))
    discount_total: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    total: Mapped[float] = mapped_column(Numeric(10, 2))
    payment_method: Mapped[PaymentMethod] = mapped_column(SAEnum(PaymentMethod))
    payment_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tendered: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    change_given: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Guest checkout (no Customer account) — used when customer_id is null.
    guest_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    guest_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    guest_email: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    # Online ordering (restaurant platform). Null fulfillment_type means a
    # normal in-store POS sale — fulfillment_status only applies otherwise.
    fulfillment_type: Mapped[Optional[FulfillmentType]] = mapped_column(SAEnum(FulfillmentType), nullable=True)
    fulfillment_status: Mapped[Optional[FulfillmentStatus]] = mapped_column(SAEnum(FulfillmentStatus), nullable=True)
    delivery_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requested_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    accepted_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    loyalty_points_redeemed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    table_id: Mapped[Optional[int]] = mapped_column(ForeignKey("restaurant_tables.id"), nullable=True)

    items: Mapped[List["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    cashier: Mapped[Optional["User"]] = relationship(foreign_keys=[cashier_id])
    accepted_by: Mapped[Optional["User"]] = relationship(foreign_keys=[accepted_by_id])
    customer: Mapped[Optional["Customer"]] = relationship()
    discount: Mapped[Optional["Discount"]] = relationship()
    table: Mapped[Optional["RestaurantTable"]] = relationship()

    @property
    def discount_code(self) -> Optional[str]:
        return self.discount.code if self.discount else None

    @property
    def table_label(self) -> Optional[str]:
        return self.table.label if self.table else None


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    qty: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2))
    tax_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    discount_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    line_total: Mapped[float] = mapped_column(Numeric(10, 2))
    returned_qty: Mapped[int] = mapped_column(Integer, default=0)
    special_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()

    @property
    def product_name(self) -> Optional[str]:
        return self.product.name if self.product else None


class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    reason: Mapped[str] = mapped_column(String(255))
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    processed_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[List["RefundItem"]] = relationship(back_populates="refund", cascade="all, delete-orphan")


class RefundItem(Base):
    __tablename__ = "refund_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    refund_id: Mapped[int] = mapped_column(ForeignKey("refunds.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    qty: Mapped[int] = mapped_column(Integer)
    line_total: Mapped[float] = mapped_column(Numeric(10, 2))

    refund: Mapped["Refund"] = relationship(back_populates="items")
