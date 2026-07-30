from pydantic import BaseModel

from app.schemas.order import OrderOut


class CheckoutSessionOut(BaseModel):
    order: OrderOut
    checkout_url: str


class PublicOrderStatusOut(BaseModel):
    order: OrderOut
