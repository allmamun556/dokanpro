from typing import Optional
from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def log_action(
    db: Session,
    user_id: Optional[int],
    action: str,
    entity: str,
    entity_id: Optional[int] = None,
    meta: Optional[dict] = None,
    *,
    business_id: int,
):
    entry = AuditLog(
        business_id=business_id,
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        meta=meta,
    )
    db.add(entry)
    db.flush()
