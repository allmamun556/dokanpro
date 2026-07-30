import re

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import create_access_token
from app.core.rate_limit import limiter
from app.models import Business
from app.models.notification import NotificationChannel
from app.schemas.signup import SignupRequest, SignupOut, SlugAvailability
from app.schemas.user import UserOut
from app.services.tenant_service import create_business
from app.services import notification_service

router = APIRouter(prefix="/signup", tags=["signup"])

_SLUG_RE = re.compile(r"^[a-z0-9-]{3,50}$")
_RESERVED_SLUGS = {"api", "t", "css", "js", "uploads", "site", "admin", "www", "static"}


def _validate_slug(slug: str) -> None:
    if not _SLUG_RE.match(slug):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Slug must be 3-50 characters, lowercase letters, numbers, and hyphens only",
        )
    if slug in _RESERVED_SLUGS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That slug is reserved, please choose another")


@router.get("/check-slug", response_model=SlugAvailability)
def check_slug(slug: str, db: Session = Depends(get_db)):
    try:
        _validate_slug(slug)
    except HTTPException:
        return SlugAvailability(available=False)
    taken = db.query(Business).filter(Business.slug == slug).first() is not None
    return SlugAvailability(available=not taken)


@router.post("", response_model=SignupOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def signup(payload: SignupRequest, request: Request, db: Session = Depends(get_db)):
    _validate_slug(payload.slug)

    if db.query(Business).filter(Business.slug == payload.slug).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "That URL is already taken — please choose another")

    business, admin = create_business(
        db,
        name=payload.business_name,
        slug=payload.slug,
        admin_name=payload.admin_name,
        admin_email=payload.admin_email,
        admin_password=payload.admin_password,
    )

    try:
        notification_service.send(
            db,
            recipient_email=payload.admin_email,
            channel=NotificationChannel.email,
            event_type="business_welcome",
            subject=f"Welcome to DokanPro, {business.name}!",
            body=(
                f"Your restaurant account is ready. Staff login: /t/{business.slug}/\n"
                f"Public site: /t/{business.slug}/site/"
            ),
            business_id=business.id,
        )
        db.commit()
    except Exception:
        # Welcome email is a nicety, never block account creation on it.
        db.rollback()

    token = create_access_token({
        "sub": str(admin.id), "role": admin.role.value, "type": "staff", "business_id": business.id,
    })
    return SignupOut(access_token=token, user=UserOut.model_validate(admin), business_slug=business.slug)
