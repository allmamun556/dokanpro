import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.rate_limit import limiter
from app.models.newsletter import NewsletterSubscriber
from app.schemas.newsletter import NewsletterSubscribe

router = APIRouter(prefix="/newsletter", tags=["public-newsletter"])


@router.post("/subscribe", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
def subscribe(payload: NewsletterSubscribe, request: Request, db: Session = Depends(get_db)):
    if request.state.business_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unable to determine which restaurant this subscription belongs to")

    existing = db.query(NewsletterSubscriber).filter(NewsletterSubscriber.email == payload.email).first()
    if existing:
        existing.is_subscribed = True
        existing.unsubscribed_at = None
    else:
        db.add(
            NewsletterSubscriber(
                business_id=request.state.business_id,
                email=payload.email,
                unsubscribe_token=secrets.token_urlsafe(32),
            )
        )
    db.commit()


@router.get("/unsubscribe")
def unsubscribe(token: str, db: Session = Depends(get_db)):
    sub = db.query(NewsletterSubscriber).filter(NewsletterSubscriber.unsubscribe_token == token).first()
    if sub is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid unsubscribe link")
    sub.is_subscribed = False
    sub.unsubscribed_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "unsubscribed"}
