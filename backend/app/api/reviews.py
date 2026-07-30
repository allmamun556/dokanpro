from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_permission
from app.models.customer import Customer
from app.models.review import Review
from app.models.user import User
from app.schemas.review import ReviewOut, ReviewReply
from app.services.audit_service import log_action

router = APIRouter(prefix="/reviews", tags=["reviews"])

MANAGE = Depends(require_permission("reviews.manage"))


def _to_out(review: Review, customer_name: str) -> ReviewOut:
    return ReviewOut(
        id=review.id,
        product_id=review.product_id,
        customer_name=customer_name,
        rating=review.rating,
        comment=review.comment,
        admin_reply=review.admin_reply,
        admin_reply_at=review.admin_reply_at,
        created_at=review.created_at,
    )


@router.get("", response_model=list[ReviewOut], dependencies=[Depends(get_current_user)])
def list_reviews(
    product_id: int | None = None,
    unanswered: bool = False,
    db: Session = Depends(get_db),
):
    query = db.query(Review, Customer.name).join(Customer, Review.customer_id == Customer.id)
    if product_id is not None:
        query = query.filter(Review.product_id == product_id)
    if unanswered:
        query = query.filter(Review.admin_reply.is_(None))
    rows = query.order_by(Review.created_at.desc()).all()
    return [_to_out(review, name) for review, name in rows]


@router.post("/{review_id}/reply", response_model=ReviewOut, dependencies=[MANAGE])
def reply_to_review(
    review_id: int,
    payload: ReviewReply,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Review not found")

    review.admin_reply = payload.reply
    review.admin_reply_by_id = current_user.id
    review.admin_reply_at = datetime.now(timezone.utc)
    log_action(db, current_user.id, "reply", "review", review.id, business_id=current_user.business_id)
    db.commit()
    db.refresh(review)

    customer = db.get(Customer, review.customer_id)
    return _to_out(review, customer.name if customer else "")
