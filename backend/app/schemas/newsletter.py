from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr


class NewsletterSubscribe(BaseModel):
    email: EmailStr


class NewsletterSubscriberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    is_subscribed: bool
    subscribed_at: datetime
    unsubscribed_at: Optional[datetime] = None
