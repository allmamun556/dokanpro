from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, func, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"
    __table_args__ = (UniqueConstraint("business_id", "email", name="uq_newsletter_business_email"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(150), index=True)
    unsubscribe_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    is_subscribed: Mapped[bool] = mapped_column(Boolean, default=True)
    subscribed_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    unsubscribed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
