from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import verify_password, create_access_token
from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.user import Token, UserOut
from app.services.audit_service import log_action

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Staff log in from /t/{slug}/, so the tenant middleware has already
    # resolved business_id from the path — without it, a query here would be
    # unscoped and could match a same-email user at a different business.
    if request.state.business_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unable to determine which business this login belongs to")

    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User account is disabled")

    token = create_access_token({"sub": str(user.id), "role": user.role.value, "type": "staff", "business_id": user.business_id})
    log_action(db, user.id, "login", "user", user.id, business_id=user.business_id)
    db.commit()

    return Token(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
