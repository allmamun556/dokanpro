from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, model_validator


class StockTransferCreate(BaseModel):
    product_id: int
    from_store_id: int
    to_store_id: int
    qty: int
    note: Optional[str] = None

    @model_validator(mode="after")
    def validate_stores_differ(self):
        if self.from_store_id == self.to_store_id:
            raise ValueError("from_store_id and to_store_id must be different")
        if self.qty <= 0:
            raise ValueError("qty must be positive")
        return self


class StockTransferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    from_store_id: int
    to_store_id: int
    qty: int
    note: Optional[str] = None
    created_at: datetime
