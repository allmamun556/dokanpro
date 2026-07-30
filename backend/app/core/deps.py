from typing import Generator, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.models.customer import Customer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def require_tenant(request: Request) -> None:
    """
    Guard for anonymous public endpoints that read tenant-scoped data.
    Without a resolved business_id, get_db() doesn't install its query
    filter at all — an unscoped query would return every business's rows
    mixed together instead of failing safely. Any public_*.py endpoint
    reachable without authentication (which itself supplies business_id via
    the JWT) must depend on this.
    """
    if request.state.business_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unable to determine which restaurant this request belongs to")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    # Missing "type" claim = a staff token issued before this claim existed.
    if payload.get("type", "staff") != "staff":
        raise credentials_exception
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise credentials_exception
    return user


customer_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/public/auth/login", auto_error=False)


def _decode_customer_token(token: Optional[str], db: Session) -> Optional[Customer]:
    if token is None:
        return None
    payload = decode_access_token(token)
    if payload is None or payload.get("type") != "customer":
        return None
    customer_id = payload.get("sub")
    if customer_id is None:
        return None
    customer = db.get(Customer, int(customer_id))
    if customer is None or customer.password_hash is None:
        return None
    return customer


def get_current_customer(
    token: str = Depends(customer_oauth2_scheme), db: Session = Depends(get_db)
) -> Customer:
    customer = _decode_customer_token(token, db)
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return customer


def get_current_customer_optional(
    token: Optional[str] = Depends(customer_oauth2_scheme), db: Session = Depends(get_db)
) -> Optional[Customer]:
    return _decode_customer_token(token, db)
