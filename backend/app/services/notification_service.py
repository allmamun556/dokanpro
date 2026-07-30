from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.notification import NotificationLog, NotificationChannel, NotificationStatus


def _send_email_via_resend(recipient_email: str, subject: str, body: str) -> bool:
    response = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
        json={
            "from": settings.RESEND_FROM_EMAIL,
            "to": [recipient_email],
            "subject": subject,
            "text": body,
        },
        timeout=10.0,
    )
    return response.status_code < 300


def send(
    db: Session,
    *,
    recipient_email: Optional[str],
    recipient_phone: Optional[str] = None,
    channel: NotificationChannel,
    event_type: str,
    subject: str,
    body: str,
    business_id: int,
) -> Optional[NotificationLog]:
    """
    Logs a notification. For the email channel, actually sends it via Resend
    when RESEND_API_KEY is configured — status reflects the real outcome
    ('sent'/'failed'). Without a key configured, or for SMS (no provider
    wired up), status stays 'pending' so this never misleadingly implies
    delivery that didn't happen.
    """
    if not recipient_email and not recipient_phone:
        return None

    status = NotificationStatus.pending
    if channel == NotificationChannel.email and recipient_email and settings.RESEND_API_KEY:
        try:
            status = NotificationStatus.sent if _send_email_via_resend(recipient_email, subject, body) else NotificationStatus.failed
        except httpx.HTTPError:
            status = NotificationStatus.failed

    log = NotificationLog(
        business_id=business_id,
        recipient_email=recipient_email,
        recipient_phone=recipient_phone,
        channel=channel,
        event_type=event_type,
        subject=subject,
        body=body,
        status=status,
    )
    db.add(log)
    db.flush()
    return log
