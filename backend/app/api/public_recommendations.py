from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_customer_optional, require_tenant
from app.models.customer import Customer
from app.schemas.recommendation import RecommendationsOut
from app.services.recommendation_service import get_recommendations

router = APIRouter(prefix="/recommendations", tags=["public-recommendations"], dependencies=[Depends(require_tenant)])


@router.get("", response_model=RecommendationsOut)
def recommendations(
    db: Session = Depends(get_db),
    customer: Optional[Customer] = Depends(get_current_customer_optional),
):
    return get_recommendations(db, customer)
