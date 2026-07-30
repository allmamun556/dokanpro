from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_permission
from app.models.newsletter import NewsletterSubscriber
from app.models.user import User
from app.schemas.newsletter import NewsletterSubscriberOut
from app.services.audit_service import log_action

router = APIRouter(prefix="/newsletter", tags=["newsletter"])

MANAGE = Depends(require_permission("customers.manage"))


@router.get("/subscribers", response_model=list[NewsletterSubscriberOut], dependencies=[MANAGE])
def list_subscribers(db: Session = Depends(get_db)):
    return db.query(NewsletterSubscriber).order_by(NewsletterSubscriber.subscribed_at.desc()).all()


@router.delete("/subscribers/{subscriber_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[MANAGE])
def delete_subscriber(subscriber_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sub = db.get(NewsletterSubscriber, subscriber_id)
    if sub is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subscriber not found")
    db.delete(sub)
    log_action(db, current_user.id, "delete", "newsletter_subscriber", subscriber_id, {"email": sub.email}, business_id=current_user.business_id)
    db.commit()
