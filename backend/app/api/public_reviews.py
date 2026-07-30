from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_customer, require_tenant
from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.models.review import Review
from app.schemas.review import ReviewCreate, ReviewOut

router = APIRouter(tags=["public-reviews"], dependencies=[Depends(require_tenant)])


def _display_name(name: str) -> str:
    """Light anonymization for public display: "Anna Schmidt" -> "Anna S."."""
    parts = name.strip().split()
    if len(parts) < 2:
        return name
    return f"{parts[0]} {parts[-1][0]}."


def _to_out(review: Review, customer_name: str) -> ReviewOut:
    return ReviewOut(
        id=review.id,
        product_id=review.product_id,
        customer_name=_display_name(customer_name),
        rating=review.rating,
        comment=review.comment,
        admin_reply=review.admin_reply,
        admin_reply_at=review.admin_reply_at,
        created_at=review.created_at,
    )


@router.get("/menu/products/{product_id}/reviews", response_model=list[ReviewOut])
def list_product_reviews(product_id: int, db: Session = Depends(get_db)):
    reviews = (
        db.query(Review, Customer.name)
        .join(Customer, Review.customer_id == Customer.id)
        .filter(Review.product_id == product_id)
        .order_by(Review.created_at.desc())
        .all()
    )
    return [_to_out(review, name) for review, name in reviews]


@router.post("/reviews", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def submit_review(
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer),
):
    verifying_item = (
        db.query(OrderItem)
        .join(Order, OrderItem.order_id == Order.id)
        .filter(Order.customer_id == customer.id, OrderItem.product_id == payload.product_id)
        .first()
    )
    if verifying_item is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can only review items you've ordered")

    review = Review(
        business_id=customer.business_id,
        product_id=payload.product_id,
        customer_id=customer.id,
        order_id=verifying_item.order_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(review)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "You've already reviewed this item")
    db.refresh(review)
    return _to_out(review, customer.name)
