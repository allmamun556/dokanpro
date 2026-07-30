from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class HeldSaleItem(BaseModel):
    product_id: int
    qty: int


class HeldSaleCreate(BaseModel):
    store_id: int = 1
    customer_id: Optional[int] = None
    items: List[HeldSaleItem]
    discount_code: Optional[str] = None
    note: Optional[str] = None


class HeldSaleOut(BaseModel):
    id: int
    store_id: int
    customer_id: Optional[int] = None
    items: List[HeldSaleItem]
    discount_code: Optional[str] = None
    note: Optional[str] = None
    created_by_name: str
    created_at: datetime
