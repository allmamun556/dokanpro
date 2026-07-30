from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory import Inventory, StockMovement, MovementReason
from app.models.transfer import StockTransfer
from app.models.user import User
from app.schemas.transfer import StockTransferCreate
from app.services.audit_service import log_action


def create_transfer(db: Session, transfer_in: StockTransferCreate, user: User) -> StockTransfer:
    """
    Moves stock for one product between two stores atomically: decrements
    the source, increments the destination, and logs both movements.
    Inventory rows are locked in a fixed order (ascending store_id) to
    avoid deadlocking against a concurrent transfer running in reverse.
    """
    try:
        store_ids_in_lock_order = sorted([transfer_in.from_store_id, transfer_in.to_store_id])
        locked_rows = {}
        for store_id in store_ids_in_lock_order:
            inv = db.execute(
                select(Inventory)
                .where(Inventory.product_id == transfer_in.product_id, Inventory.store_id == store_id)
                .with_for_update()
            ).scalar_one_or_none()
            locked_rows[store_id] = inv

        source_inv = locked_rows[transfer_in.from_store_id]
        if source_inv is None or source_inv.quantity < transfer_in.qty:
            have = source_inv.quantity if source_inv else 0
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Insufficient stock at source store: have {have}, requested {transfer_in.qty}",
            )

        dest_inv = locked_rows[transfer_in.to_store_id]
        if dest_inv is None:
            dest_inv = Inventory(business_id=user.business_id, product_id=transfer_in.product_id, store_id=transfer_in.to_store_id, quantity=0)
            db.add(dest_inv)
            db.flush()

        source_inv.quantity -= transfer_in.qty
        dest_inv.quantity += transfer_in.qty

        transfer = StockTransfer(
            business_id=user.business_id,
            product_id=transfer_in.product_id,
            from_store_id=transfer_in.from_store_id,
            to_store_id=transfer_in.to_store_id,
            qty=transfer_in.qty,
            note=transfer_in.note,
            created_by=user.id,
        )
        db.add(transfer)
        db.flush()
        reference = f"transfer:{transfer.id}"

        db.add(
            StockMovement(
                business_id=user.business_id,
                product_id=transfer_in.product_id,
                store_id=transfer_in.from_store_id,
                change_qty=-transfer_in.qty,
                reason=MovementReason.transfer_out,
                created_by=user.id,
                reference=reference,
            )
        )
        db.add(
            StockMovement(
                business_id=user.business_id,
                product_id=transfer_in.product_id,
                store_id=transfer_in.to_store_id,
                change_qty=transfer_in.qty,
                reason=MovementReason.transfer_in,
                created_by=user.id,
                reference=reference,
            )
        )

        log_action(db, user.id, "transfer", "product", transfer_in.product_id, {
            "from_store_id": transfer_in.from_store_id,
            "to_store_id": transfer_in.to_store_id,
            "qty": transfer_in.qty,
        }, business_id=user.business_id)

        db.commit()
        db.refresh(transfer)
        return transfer

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
