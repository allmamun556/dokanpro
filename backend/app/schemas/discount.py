from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator

from app.models.discount import DiscountType


class DiscountCreate(BaseModel):
    code: str
    name: str
    type: DiscountType
    value: float
    min_subtotal: float = 0
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("value")
    @classmethod
    def value_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("value must be positive")
        return v


class DiscountUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[DiscountType] = None
    value: Optional[float] = None
    min_subtotal: Optional[float] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class DiscountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    type: DiscountType
    value: float
    min_subtotal: float
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_active: bool


class DiscountPreview(BaseModel):
    id: int
    code: str
    name: str
    type: DiscountType
    value: float
    discount_amount: float
