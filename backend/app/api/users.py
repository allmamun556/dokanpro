from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_permission, PERMISSIONS
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services.audit_service import log_action

router = APIRouter(prefix="/users", tags=["users"])

MANAGE = Depends(require_permission("users.manage"))


@router.get("/permissions")
def list_permissions(current_user: User = Depends(get_current_user)):
    return [{"key": key, "label": label, "description": desc} for key, label, desc in PERMISSIONS]


@router.get("", response_model=list[UserOut], dependencies=[MANAGE])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.id).all()


@router.post("", response_model=UserOut, dependencies=[MANAGE])
def create_user(payload: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")
    user = User(
        business_id=current_user.business_id,
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        phone=payload.phone,
        position=payload.position,
        hire_date=payload.hire_date,
        salary=payload.salary,
        permission_overrides=payload.permission_overrides,
    )
    db.add(user)
    db.flush()
    log_action(db, current_user.id, "create", "user", user.id, business_id=current_user.business_id)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut, dependencies=[MANAGE])
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    data = payload.model_dump(exclude_unset=True)
    if "password" in data and data["password"]:
        user.password_hash = hash_password(data.pop("password"))
    for field, value in data.items():
        setattr(user, field, value)
    log_action(db, current_user.id, "update", "user", user.id, business_id=current_user.business_id)
    db.commit()
    db.refresh(user)
    return user
