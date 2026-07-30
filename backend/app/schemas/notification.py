from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.models.notification import NotificationChannel, NotificationStatus


class NotificationLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    recipient_email: Optional[str] = None
    recipient_phone: Optional[str] = None
    channel: NotificationChannel
    event_type: str
    subject: str
    body: str
    status: NotificationStatus
    created_at: datetime
