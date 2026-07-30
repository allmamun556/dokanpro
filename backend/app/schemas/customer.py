from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CustomerCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    loyalty_points: Optional[int] = None


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    loyalty_points: int
    total_spent: float = 0
    last_purchase: Optional[datetime] = None
