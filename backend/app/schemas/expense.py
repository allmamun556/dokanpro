from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class ExpenseCreate(BaseModel):
    store_id: int = 1
    category: str
    description: Optional[str] = None
    amount: float
    expense_date: date


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    store_id: int
    category: str
    description: Optional[str] = None
    amount: float
    expense_date: date
    created_by: int
    created_at: datetime
