from typing import Optional
from pydantic import BaseModel, ConfigDict


class StoreCreate(BaseModel):
    name: str
    address: Optional[str] = None


class StoreUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None


class StoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    address: Optional[str] = None
