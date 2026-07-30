from typing import Optional

from sqlalchemy import String, Numeric, Boolean, Date, ForeignKey, Text, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("business_id", "name", name="uq_categories_business_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))


class Brand(Base):
    __tablename__ = "brands"
    __table_args__ = (UniqueConstraint("business_id", "name", name="uq_brands_business_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))


class Unit(Base):
    __tablename__ = "units"
    __table_args__ = (UniqueConstraint("business_id", "name", name="uq_units_business_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(50))
    abbreviation: Mapped[str] = mapped_column(String(10))


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("business_id", "sku", name="uq_products_business_sku"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    sku: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(200))
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True)
    brand_id: Mapped[Optional[int]] = mapped_column(ForeignKey("brands.id"), nullable=True)
    unit_id: Mapped[Optional[int]] = mapped_column(ForeignKey("units.id"), nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    tax_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expiry_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Menu/online-ordering fields (restaurant platform)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    allergens: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    calories: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_available_online: Mapped[bool] = mapped_column(Boolean, default=True)

    category: Mapped[Optional["Category"]] = relationship()
    brand: Mapped[Optional["Brand"]] = relationship()
    unit: Mapped[Optional["Unit"]] = relationship()
