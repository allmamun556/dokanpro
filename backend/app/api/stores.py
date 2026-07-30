from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_permission
from app.models.store import Store
from app.schemas.store import StoreCreate, StoreUpdate, StoreOut

router = APIRouter(prefix="/stores", tags=["stores"])

MANAGE = Depends(require_permission("stores.manage"))


@router.get("", response_model=list[StoreOut])
def list_stores(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(Store).order_by(Store.name).all()


@router.post("", response_model=StoreOut, status_code=status.HTTP_201_CREATED, dependencies=[MANAGE])
def create_store(payload: StoreCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    store = Store(business_id=current_user.business_id, **payload.model_dump())
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@router.patch("/{store_id}", response_model=StoreOut, dependencies=[MANAGE])
def update_store(store_id: int, payload: StoreUpdate, db: Session = Depends(get_db)):
    store = db.get(Store, store_id)
    if not store:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Store not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(store, field, value)
    db.commit()
    db.refresh(store)
    return store
