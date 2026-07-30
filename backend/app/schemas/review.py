from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator


class ReviewCreate(BaseModel):
    product_id: int
    rating: int
    comment: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def rating_range(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("rating must be between 1 and 5")
        return v


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    customer_name: str
    rating: int
    comment: Optional[str] = None
    admin_reply: Optional[str] = None
    admin_reply_at: Optional[datetime] = None
    created_at: datetime


class ReviewReply(BaseModel):
    reply: str
