from app.models import (
    Store, User, Customer, Category, Brand, Unit, Product, Discount,
    Order, OrderItem, Refund, RefundItem, Purchase, PurchaseItem,
    PurchasePayment, PurchaseReturn, PurchaseReturnItem, Supplier, Expense,
    Reservation, RestaurantTable, HeldSale, Inventory, StockMovement,
    StockTransfer, Review, NewsletterSubscriber, NotificationLog, AuditLog,
)

# Every model whose rows belong to exactly one tenant. get_db() applies a
# with_loader_criteria filter for each of these to every session, so every
# ORM SELECT is automatically tenant-scoped without touching query logic in
# the ~27 API routers. Business itself is deliberately excluded — it IS the
# tenant, not owned by one.
TENANT_SCOPED_MODELS = [
    Store, User, Customer, Category, Brand, Unit, Product, Discount,
    Order, OrderItem, Refund, RefundItem, Purchase, PurchaseItem,
    PurchasePayment, PurchaseReturn, PurchaseReturnItem, Supplier, Expense,
    Reservation, RestaurantTable, HeldSale, Inventory, StockMovement,
    StockTransfer, Review, NewsletterSubscriber, NotificationLog, AuditLog,
]
