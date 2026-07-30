from datetime import datetime
from pydantic import BaseModel

from app.models.inventory import MovementReason


class StockAdjust(BaseModel):
    product_id: int
    store_id: int = 1
    change_qty: int
    reason: MovementReason
    reference: str | None = None


class InventoryOut(BaseModel):
    product_id: int
    store_id: int
    quantity: int
    reorder_level: int
    product_name: str
    sku: str


class StockMovementOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    sku: str
    store_id: int
    change_qty: int
    reason: MovementReason
    reference: str | None = None
    created_by_name: str | None = None
    created_at: datetime
