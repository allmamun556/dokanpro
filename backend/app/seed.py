"""
Quick-start helper: seeds default data - an admin user, a store, a couple of
categories/products - into an already-migrated database.

Usage:
    python -m app.seed

Schema is owned by Alembic (see /alembic); run `alembic upgrade head` first.
"""
from app.db.session import SessionLocal
from app.core.security import hash_password

from app.models import (  # noqa: F401
    Business, User, RoleEnum, Store, Category, Product, Inventory, StockMovement,
    Customer, Order, OrderItem, Refund, Discount, DiscountType, AuditLog,
    RestaurantTable,
)


def run():
    db = SessionLocal()
    try:
        # The multi_tenancy_foundation migration always creates this business
        # (backfilling every pre-existing row onto it) — this lookup only
        # falls back to creating it itself for a brand-new DB where that
        # migration's own INSERT somehow didn't run.
        business = db.query(Business).filter(Business.slug == "bavaria-genuss").first()
        if business is None:
            business = Business(name="Bavaria Genuss Restaurant", slug="bavaria-genuss")
            db.add(business)
            db.commit()
            db.refresh(business)

        if not db.query(Store).filter(Store.business_id == business.id).first():
            # No explicit id: a hardcoded id=1 here would desync the stores_id_seq
            # sequence from its actual max(id), breaking the next auto-assigned
            # insert (e.g. create_tenant.py's store for a second business).
            db.add(Store(business_id=business.id, name="Main Store", address="123 Market Street"))

        if not db.query(User).filter(User.business_id == business.id, User.email == "admin@possystem.dev").first():
            db.add(User(
                business_id=business.id,
                name="Admin",
                email="admin@possystem.dev",
                password_hash=hash_password("admin123"),
                role=RoleEnum.admin,
            ))
            db.add(User(
                business_id=business.id,
                name="Sample Manager",
                email="manager@possystem.dev",
                password_hash=hash_password("manager123"),
                role=RoleEnum.manager,
            ))
            db.add(User(
                business_id=business.id,
                name="Sample Cashier",
                email="cashier@possystem.dev",
                password_hash=hash_password("cashier123"),
                role=RoleEnum.cashier,
            ))
        db.commit()

        if not db.query(Category).filter(Category.business_id == business.id).first():
            beverages = Category(business_id=business.id, name="Beverages")
            snacks = Category(business_id=business.id, name="Snacks")
            household = Category(business_id=business.id, name="Household")
            db.add_all([beverages, snacks, household])
            db.commit()

            sample_products = [
                ("SKU-0001", "Bottled Water 500ml", beverages.id, 1.50, 0.60, 0, 100, 20),
                ("SKU-0002", "Cola Can 330ml", beverages.id, 1.80, 0.70, 7, 80, 15),
                ("SKU-0003", "Potato Chips 150g", snacks.id, 2.50, 1.10, 7, 50, 10),
                ("SKU-0004", "Chocolate Bar", snacks.id, 1.20, 0.45, 7, 60, 10),
                ("SKU-0005", "Dish Soap 500ml", household.id, 3.20, 1.50, 19, 30, 5),
                ("SKU-0006", "Paper Towels 2-pack", household.id, 4.00, 2.00, 19, 4, 5),
            ]
            for sku, name, cat_id, price, cost, tax, qty, reorder in sample_products:
                p = Product(business_id=business.id, sku=sku, name=name, category_id=cat_id, price=price, cost=cost, tax_rate=tax)
                db.add(p)
                db.flush()
                db.add(Inventory(business_id=business.id, product_id=p.id, store_id=1, quantity=qty, reorder_level=reorder))
            db.commit()

        if not db.query(Discount).filter(Discount.business_id == business.id, Discount.code == "WELCOME10").first():
            db.add(Discount(
                business_id=business.id,
                code="WELCOME10",
                name="Welcome 10% off",
                type=DiscountType.percentage,
                value=10,
                min_subtotal=0,
                is_active=True,
            ))
            db.commit()

        if not db.query(RestaurantTable).filter(RestaurantTable.business_id == business.id).first():
            db.add_all([
                RestaurantTable(business_id=business.id, store_id=1, label="T1", capacity=2),
                RestaurantTable(business_id=business.id, store_id=1, label="T2", capacity=2),
                RestaurantTable(business_id=business.id, store_id=1, label="T3", capacity=4),
                RestaurantTable(business_id=business.id, store_id=1, label="T4", capacity=4),
                RestaurantTable(business_id=business.id, store_id=1, label="T5", capacity=6),
                RestaurantTable(business_id=business.id, store_id=1, label="Patio 1", capacity=4),
            ])
            db.commit()

        print("Seed complete.")
        print(f"Business: {business.name} (slug: {business.slug})")
        print(f"Login at /t/{business.slug}/ with: admin@possystem.dev / admin123 (also manager@possystem.dev / manager123, cashier@possystem.dev / cashier123)")
    finally:
        db.close()


if __name__ == "__main__":
    run()
