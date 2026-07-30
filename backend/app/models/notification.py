import enum
from typing import Optional

from sqlalchemy import String, Text, Enum as SAEnum, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificationChannel(str, enum.Enum):
    email = "email"
    sms = "sms"


class NotificationStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


class NotificationLog(Base):
    """
    A record of a notification. Email is sent for real via Resend when
    RESEND_API_KEY is configured (status reflects the real outcome). SMS has
    no provider wired up yet — status stays 'pending' for that channel so
    this never misleadingly implies delivery that didn't happen.
    """

    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    recipient_email: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    recipient_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    channel: Mapped[NotificationChannel] = mapped_column(SAEnum(NotificationChannel))
    event_type: Mapped[str] = mapped_column(String(50))
    subject: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[NotificationStatus] = mapped_column(SAEnum(NotificationStatus), default=NotificationStatus.pending)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
