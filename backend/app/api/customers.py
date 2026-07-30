from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_permission
from app.models.customer import Customer
from app.models.order import Order, OrderStatus
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerOut

router = APIRouter(prefix="/customers", tags=["customers"])

MANAGE = Depends(require_permission("customers.manage"))


def _purchase_stats(db: Session) -> dict:
    rows = (
        db.query(
            Order.customer_id,
            func.coalesce(func.sum(Order.total), 0).label("total_spent"),
            func.max(Order.created_at).label("last_purchase"),
        )
        .filter(Order.customer_id.isnot(None), Order.status != OrderStatus.voided)
        .group_by(Order.customer_id)
        .all()
    )
    return {row.customer_id: (float(row.total_spent), row.last_purchase) for row in rows}


def _to_out(customer: Customer, stats: dict) -> CustomerOut:
    total_spent, last_purchase = stats.get(customer.id, (0.0, None))
    return CustomerOut(
        id=customer.id,
        name=customer.name,
        phone=customer.phone,
        email=customer.email,
        loyalty_points=customer.loyalty_points,
        total_spent=total_spent,
        last_purchase=last_purchase,
    )


@router.get("", response_model=list[CustomerOut])
def list_customers(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    customers = db.query(Customer).order_by(Customer.name).all()
    stats = _purchase_stats(db)
    return [_to_out(c, stats) for c in customers]


@router.post("", response_model=CustomerOut)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    customer = Customer(business_id=current_user.business_id, **payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return _to_out(customer, {})


@router.patch("/{customer_id}", response_model=CustomerOut, dependencies=[MANAGE])
def update_customer(customer_id: int, payload: CustomerUpdate, db: Session = Depends(get_db)):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    db.commit()
    db.refresh(customer)
    return _to_out(customer, _purchase_stats(db))


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return _to_out(customer, _purchase_stats(db))
