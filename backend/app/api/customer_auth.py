from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.deps import get_current_customer
from app.core.rate_limit import limiter
from app.models.customer import Customer
from app.schemas.customer import CustomerOut
from app.schemas.customer_auth import CustomerRegister, CustomerToken

# Password reset (forgot-password) is out of scope for Phase 1 — no email
# delivery infra exists in this codebase yet.
router = APIRouter(prefix="/auth", tags=["customer-auth"])


def _to_out(customer: Customer) -> CustomerOut:
    return CustomerOut(
        id=customer.id,
        name=customer.name,
        phone=customer.phone,
        email=customer.email,
        loyalty_points=customer.loyalty_points,
        total_spent=0.0,
        last_purchase=None,
    )


@router.post("/register", response_model=CustomerToken)
@limiter.limit("5/minute")
def register(payload: CustomerRegister, request: Request, db: Session = Depends(get_db)):
    # Anonymous request — no logged-in customer to read business_id off of
    # yet, so it comes from the /t/{slug}/ page the signup form was on
    # (resolved by the tenant middleware into request.state.business_id).
    if request.state.business_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unable to determine which restaurant this signup belongs to")

    existing = db.query(Customer).filter(Customer.email == payload.email).first()
    if existing and existing.password_hash is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "An account with this email already exists")

    if existing is not None:
        # A staff-created CRM record with this email but no login yet — link
        # to it rather than creating a duplicate, to preserve order history.
        customer = existing
        customer.name = payload.name
        if payload.phone:
            customer.phone = payload.phone
    else:
        customer = Customer(
            business_id=request.state.business_id,
            name=payload.name, email=payload.email, phone=payload.phone,
        )
        db.add(customer)

    customer.password_hash = hash_password(payload.password)
    customer.is_verified = True  # no email-verification infra yet (Phase 1)
    db.commit()
    db.refresh(customer)

    token = create_access_token({"sub": str(customer.id), "type": "customer", "business_id": customer.business_id})
    return CustomerToken(access_token=token, customer=_to_out(customer))


@router.post("/login", response_model=CustomerToken)
@limiter.limit("10/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    if request.state.business_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unable to determine which restaurant this login belongs to")

    customer = db.query(Customer).filter(Customer.email == form_data.username).first()
    if not customer or customer.password_hash is None or not verify_password(form_data.password, customer.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")

    token = create_access_token({"sub": str(customer.id), "type": "customer", "business_id": customer.business_id})
    return CustomerToken(access_token=token, customer=_to_out(customer))


@router.get("/me", response_model=CustomerOut)
def me(current_customer: Customer = Depends(get_current_customer)):
    return _to_out(current_customer)
