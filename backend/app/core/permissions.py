from fastapi import Depends, HTTPException, status

from app.core.deps import get_current_user
from app.models.user import User, RoleEnum

# (key, label, description) — this list also drives the permissions matrix UI on the Users page.
PERMISSIONS = [
    ("products.manage", "Manage Products", "Create, edit, and deactivate products, categories, brands, and units"),
    ("inventory.adjust", "Adjust Inventory", "Manually adjust stock quantities"),
    ("discounts.manage", "Manage Discounts", "Create and edit discount codes"),
    ("customers.manage", "Manage Customers", "Edit customer details and loyalty points"),
    ("suppliers.manage", "Manage Suppliers", "Create and edit supplier records"),
    ("purchases.manage", "Manage Purchases", "Record purchases, purchase returns, and supplier payments"),
    ("transfers.manage", "Manage Stock Transfers", "Move stock between stores"),
    ("expenses.manage", "Manage Expenses", "Record and delete business expenses"),
    ("stores.manage", "Manage Stores", "Create and edit store locations"),
    ("orders.refund", "Process Refunds", "Process sales returns and refunds"),
    ("reports.profit", "View Profit Reports", "View profit/loss figures and the dashboard's profit stats"),
    ("users.manage", "Manage Users", "Create, edit, and manage user accounts"),
    ("settings.manage", "Manage Settings", "Edit business-wide settings"),
    ("orders.fulfill", "Manage Online Orders", "View and update the status of online pickup/delivery orders"),
    ("reservations.manage", "Manage Reservations", "Confirm, seat, and manage table reservations"),
    ("reviews.manage", "Manage Reviews", "Reply to customer reviews"),
    ("tables.manage", "Manage Tables", "View and update table status, print table QR codes, and start dine-in orders"),
]
PERMISSION_KEYS = {key for key, _, _ in PERMISSIONS}

# What each role gets when a user has no explicit override for a given key.
# This exactly reproduces the app's pre-existing admin/manager/cashier behavior.
ROLE_DEFAULTS: dict[RoleEnum, set] = {
    RoleEnum.admin: set(PERMISSION_KEYS),
    RoleEnum.manager: PERMISSION_KEYS - {"users.manage", "settings.manage"},
    # Front-counter staff handle online order status day-to-day in a restaurant.
    RoleEnum.cashier: {"orders.fulfill"},
    # Waiters get the same day-to-day access as cashiers (checkout + online
    # orders) plus table management (status toggling, walk-in orders).
    RoleEnum.waiter: {"orders.fulfill", "tables.manage"},
    # Kitchen staff only need the online-order queue — no checkout, no
    # customer/pricing data, no other business-management capability.
    RoleEnum.chef: {"orders.fulfill"},
}


def has_permission(user: User, key: str) -> bool:
    overrides = user.permission_overrides or {}
    if key in overrides:
        return bool(overrides[key])
    return key in ROLE_DEFAULTS.get(user.role, set())


def require_permission(key: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user, key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return user

    return checker
