from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.permissions import require_permission
from app.models.notification import NotificationLog
from app.schemas.notification import NotificationLogOut

router = APIRouter(prefix="/notifications", tags=["notifications"])

MANAGE = Depends(require_permission("settings.manage"))


@router.get("", response_model=list[NotificationLogOut], dependencies=[MANAGE])
def list_notifications(
    event_type: str | None = None,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(NotificationLog)
    if event_type is not None:
        query = query.filter(NotificationLog.event_type == event_type)
    return query.order_by(NotificationLog.id.desc()).limit(limit).all()
