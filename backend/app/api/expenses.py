from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_permission
from app.models.user import User
from app.models.expense import Expense
from app.schemas.expense import ExpenseCreate, ExpenseOut
from app.services.audit_service import log_action

router = APIRouter(prefix="/expenses", tags=["expenses"])

MANAGE = Depends(require_permission("expenses.manage"))


@router.get("", response_model=list[ExpenseOut], dependencies=[MANAGE])
def list_expenses(
    store_id: int = 1,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Expense).filter(Expense.store_id == store_id)
    if date_from is not None:
        query = query.filter(Expense.expense_date >= date_from)
    if date_to is not None:
        query = query.filter(Expense.expense_date <= date_to)
    return query.order_by(Expense.expense_date.desc(), Expense.id.desc()).all()


@router.get("/total", dependencies=[MANAGE])
def total_expenses(
    store_id: int = 1,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(func.coalesce(func.sum(Expense.amount), 0)).filter(Expense.store_id == store_id)
    if date_from is not None:
        query = query.filter(Expense.expense_date >= date_from)
    if date_to is not None:
        query = query.filter(Expense.expense_date <= date_to)
    return {"total": float(query.scalar() or 0)}


@router.post("", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED, dependencies=[MANAGE])
def create_expense(payload: ExpenseCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    expense = Expense(business_id=current_user.business_id, **payload.model_dump(), created_by=current_user.id)
    db.add(expense)
    db.flush()
    log_action(db, current_user.id, "create", "expense", expense.id, {"amount": str(payload.amount)}, business_id=current_user.business_id)
    db.commit()
    db.refresh(expense)
    return expense


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[MANAGE])
def delete_expense(expense_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    expense = db.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expense not found")
    db.delete(expense)
    log_action(db, current_user.id, "delete", "expense", expense_id, business_id=current_user.business_id)
    db.commit()
