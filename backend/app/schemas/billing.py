from typing import Optional
from pydantic import BaseModel


class SubscriptionStatusOut(BaseModel):
    subscribed: bool
    status: Optional[str] = None


class SubscribeCheckoutOut(BaseModel):
    checkout_url: str
