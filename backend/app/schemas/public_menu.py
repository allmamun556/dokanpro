from typing import Optional
from pydantic import BaseModel, ConfigDict


class PublicMenuItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    price: float
    description: Optional[str] = None
    allergens: Optional[str] = None
    calories: Optional[int] = None
    image_url: Optional[str] = None
    category_id: Optional[int] = None
    avg_rating: Optional[float] = None
    review_count: int = 0


class PublicMenuCategory(BaseModel):
    id: int
    name: str
    items: list[PublicMenuItem] = []
