from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_permission
from app.models.user import User
from app.models.transfer import StockTransfer
from app.schemas.transfer import StockTransferCreate, StockTransferOut
from app.services.transfer_service import create_transfer

router = APIRouter(prefix="/transfers", tags=["transfers"])

MANAGE = Depends(require_permission("transfers.manage"))


@router.get("", response_model=list[StockTransferOut], dependencies=[MANAGE])
def list_transfers(limit: int = Query(100, le=500), db: Session = Depends(get_db)):
    return db.query(StockTransfer).order_by(StockTransfer.id.desc()).limit(limit).all()


@router.post("", response_model=StockTransferOut, dependencies=[MANAGE])
def transfer_stock(payload: StockTransferCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return create_transfer(db, payload, current_user)
