from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import require_tenant
from app.db.session import get_db
from app.models.table import RestaurantTable
from app.schemas.public_table import PublicTableOut

router = APIRouter(prefix="/tables", tags=["public-tables"], dependencies=[Depends(require_tenant)])


@router.get("/{table_id}", response_model=PublicTableOut)
def get_table(table_id: int, db: Session = Depends(get_db)):
    """Minimal lookup for the dine-in QR landing page — just enough to confirm 'you're ordering for Table N'."""
    table = db.get(RestaurantTable, table_id)
    if table is None or not table.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Table not found")
    return table
