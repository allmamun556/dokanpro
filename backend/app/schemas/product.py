from typing import Optional
from datetime import date
from pydantic import BaseModel, ConfigDict


class CategoryCreate(BaseModel):
    name: str


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class BrandCreate(BaseModel):
    name: str


class BrandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class UnitCreate(BaseModel):
    name: str
    abbreviation: str


class UnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    abbreviation: str


class ProductCreate(BaseModel):
    sku: str
    name: str
    category_id: Optional[int] = None
    brand_id: Optional[int] = None
    unit_id: Optional[int] = None
    price: float
    cost: float = 0
    tax_rate: float = 0
    is_active: bool = True
    expiry_date: Optional[date] = None
    initial_quantity: int = 0
    reorder_level: int = 5
    description: Optional[str] = None
    allergens: Optional[str] = None
    calories: Optional[int] = None
    is_available_online: bool = True


class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    category_id: Optional[int] = None
    brand_id: Optional[int] = None
    unit_id: Optional[int] = None
    price: Optional[float] = None
    cost: Optional[float] = None
    tax_rate: Optional[float] = None
    is_active: Optional[bool] = None
    expiry_date: Optional[date] = None
    description: Optional[str] = None
    allergens: Optional[str] = None
    calories: Optional[int] = None
    is_available_online: Optional[bool] = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sku: str
    name: str
    category_id: Optional[int] = None
    brand_id: Optional[int] = None
    unit_id: Optional[int] = None
    price: float
    cost: float
    tax_rate: float
    is_active: bool
    expiry_date: Optional[date] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    allergens: Optional[str] = None
    calories: Optional[int] = None
    is_available_online: bool = True


class ProductWithStock(ProductOut):
    quantity: int = 0
    reorder_level: int = 5
