from typing import Optional
from pydantic import BaseModel


class RecommendedItem(BaseModel):
    product_id: int
    name: str
    price: float
    image_url: Optional[str] = None
    reason: str


class RecommendationsOut(BaseModel):
    weather: Optional[str] = None
    items: list[RecommendedItem] = []
