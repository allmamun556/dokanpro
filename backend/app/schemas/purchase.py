from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models.purchase import PurchaseStatus
from app.models.order import PaymentMethod


class PurchaseItemIn(BaseModel):
    product_id: int
    qty: int = Field(gt=0, le=100000)  # wholesale restock, not a diner order — higher ceiling
    unit_cost: float
    tax_rate: float = 0


class PurchaseCreate(BaseModel):
    store_id: int = 1
    supplier_id: Optional[int] = None
    invoice_number: Optional[str] = None
    items: List[PurchaseItemIn]
    discount_total: float = 0


class PurchaseItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    qty: int
    unit_cost: float
    tax_amount: float
    line_total: float
    returned_qty: int


class PurchasePaymentCreate(BaseModel):
    amount: float
    payment_date: date
    method: PaymentMethod = PaymentMethod.cash
    note: Optional[str] = None


class PurchasePaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    purchase_id: int
    amount: float
    payment_date: date
    method: PaymentMethod
    note: Optional[str] = None
    created_at: datetime


class PurchaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    store_id: int
    supplier_id: Optional[int] = None
    invoice_number: Optional[str] = None
    status: PurchaseStatus
    subtotal: float
    tax_total: float
    discount_total: float
    total: float
    paid_amount: float
    due_amount: float
    created_at: datetime
    items: List[PurchaseItemOut] = []
    payments: List[PurchasePaymentOut] = []


class PurchaseReturnItemIn(BaseModel):
    product_id: int
    qty: int = Field(gt=0, le=100000)


class PurchaseReturnCreate(BaseModel):
    reason: str
    items: List[PurchaseReturnItemIn]


class PurchaseReturnOut(BaseModel):
    id: int
    purchase_id: int
    amount: float
    reason: str
