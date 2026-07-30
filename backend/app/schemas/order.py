from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models.order import PaymentMethod, OrderStatus, FulfillmentType, FulfillmentStatus


class OrderItemIn(BaseModel):
    product_id: int
    qty: int = Field(gt=0, le=100)
    discount_amount: float = 0
    special_instructions: Optional[str] = None


class OrderCreate(BaseModel):
    store_id: int = 1
    customer_id: Optional[int] = None
    items: List[OrderItemIn]
    payment_method: PaymentMethod = PaymentMethod.cash
    payment_reference: Optional[str] = None
    tendered: Optional[float] = None
    discount_code: Optional[str] = None
    table_id: Optional[int] = None


class PublicOrderCreate(BaseModel):
    store_id: int = 1
    items: List[OrderItemIn]
    fulfillment_type: FulfillmentType
    delivery_address: Optional[str] = None
    requested_time: Optional[datetime] = None
    discount_code: Optional[str] = None
    redeem_loyalty_points: bool = False
    table_id: Optional[int] = None
    guest_name: Optional[str] = None
    guest_phone: Optional[str] = None
    guest_email: Optional[str] = None


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    product_name: Optional[str] = None
    qty: int
    unit_price: float
    tax_amount: float
    discount_amount: float
    line_total: float
    returned_qty: int
    special_instructions: Optional[str] = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    store_id: int
    cashier_id: Optional[int] = None
    customer_id: Optional[int] = None
    discount_code: Optional[str] = None
    status: OrderStatus
    subtotal: float
    tax_total: float
    discount_total: float
    total: float
    payment_method: PaymentMethod
    payment_reference: Optional[str] = None
    tendered: Optional[float] = None
    change_given: Optional[float] = None
    created_at: datetime
    items: List[OrderItemOut] = []
    guest_name: Optional[str] = None
    guest_phone: Optional[str] = None
    guest_email: Optional[str] = None
    fulfillment_type: Optional[FulfillmentType] = None
    fulfillment_status: Optional[FulfillmentStatus] = None
    delivery_address: Optional[str] = None
    requested_time: Optional[datetime] = None
    stripe_payment_intent_id: Optional[str] = None
    accepted_by_id: Optional[int] = None
    loyalty_points_redeemed: Optional[int] = None
    table_id: Optional[int] = None
    table_label: Optional[str] = None


class RefundItemIn(BaseModel):
    product_id: int
    qty: int = Field(gt=0, le=100)


class RefundCreate(BaseModel):
    reason: str
    items: List[RefundItemIn]


class RefundItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: int
    qty: int
    line_total: float


class RefundOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_id: int
    reason: str
    amount: float
    items: List[RefundItemOut] = []
