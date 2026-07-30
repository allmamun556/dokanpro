from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_permission
from app.models.order import Order, OrderItem, OrderStatus, Refund
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.expense import Expense
from app.models.user import User
from app.services.export_service import export_response

router = APIRouter(prefix="/reports", tags=["reports"])

MANAGE = Depends(require_permission("reports.profit"))


@router.get("/summary")
def summary(store_id: int = 1, days: int = 30, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    since = date.today() - timedelta(days=days)

    total_sales = (
        db.query(func.coalesce(func.sum(Order.total), 0))
        .filter(Order.store_id == store_id, Order.status != OrderStatus.voided, Order.created_at >= since)
        .scalar()
    )
    order_count = (
        db.query(func.count(Order.id))
        .filter(Order.store_id == store_id, Order.status != OrderStatus.voided, Order.created_at >= since)
        .scalar()
    )
    low_stock_count = (
        db.query(func.count(Inventory.id))
        .filter(Inventory.store_id == store_id, Inventory.quantity <= Inventory.reorder_level)
        .scalar()
    )
    product_count = db.query(func.count(Product.id)).filter(Product.is_active.is_(True)).scalar()

    return {
        "total_sales": float(total_sales or 0),
        "order_count": int(order_count or 0),
        "average_order_value": float(total_sales / order_count) if order_count else 0.0,
        "low_stock_count": int(low_stock_count or 0),
        "active_product_count": int(product_count or 0),
        "period_days": days,
    }


@router.get("/daily-sales")
def daily_sales(store_id: int = 1, days: int = 14, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    since = date.today() - timedelta(days=days)
    rows = (
        db.query(
            func.date_trunc("day", Order.created_at).label("day"),
            func.sum(Order.total).label("total"),
            func.count(Order.id).label("count"),
        )
        .filter(Order.store_id == store_id, Order.status != OrderStatus.voided, Order.created_at >= since)
        .group_by("day")
        .order_by("day")
        .all()
    )
    return [
        {"day": row.day.date().isoformat(), "total": float(row.total or 0), "count": int(row.count)}
        for row in rows
    ]


@router.get("/top-products")
def top_products(store_id: int = 1, days: int = 30, limit: int = Query(10, le=100), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    since = date.today() - timedelta(days=days)
    rows = (
        db.query(
            Product.name,
            func.sum(OrderItem.qty).label("units_sold"),
            func.sum(OrderItem.line_total).label("revenue"),
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.store_id == store_id, Order.status != OrderStatus.voided, Order.created_at >= since)
        .group_by(Product.name)
        .order_by(func.sum(OrderItem.qty).desc())
        .limit(limit)
        .all()
    )
    return [
        {"name": row.name, "units_sold": int(row.units_sold or 0), "revenue": float(row.revenue or 0)}
        for row in rows
    ]


@router.get("/sales-by-cashier")
def sales_by_cashier(store_id: int = 1, days: int = 30, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    since = date.today() - timedelta(days=days)
    rows = (
        db.query(
            User.name,
            func.count(Order.id).label("order_count"),
            func.sum(Order.total).label("total"),
        )
        .join(Order, Order.cashier_id == User.id)
        .filter(Order.store_id == store_id, Order.status != OrderStatus.voided, Order.created_at >= since)
        .group_by(User.name)
        .order_by(func.sum(Order.total).desc())
        .all()
    )
    return [
        {"cashier": row.name, "order_count": int(row.order_count), "total": float(row.total or 0)}
        for row in rows
    ]


@router.get("/low-stock")
def low_stock_report(store_id: int = 1, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (
        db.query(Inventory, Product)
        .join(Product, Product.id == Inventory.product_id)
        .filter(Inventory.store_id == store_id, Inventory.quantity <= Inventory.reorder_level)
        .order_by(Inventory.quantity)
        .all()
    )
    return [
        {
            "product_id": p.id, "name": p.name, "sku": p.sku,
            "quantity": inv.quantity, "reorder_level": inv.reorder_level,
        }
        for inv, p in rows
    ]


@router.get("/expiring")
def expiring_products(store_id: int = 1, days: int = 30, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    today = date.today()
    threshold = today + timedelta(days=days)
    rows = (
        db.query(Product, Inventory.quantity)
        .join(Inventory, Inventory.product_id == Product.id)
        .filter(
            Inventory.store_id == store_id,
            Inventory.quantity > 0,
            Product.expiry_date.isnot(None),
            Product.expiry_date <= threshold,
        )
        .order_by(Product.expiry_date)
        .all()
    )
    return [
        {
            "product_id": p.id,
            "name": p.name,
            "sku": p.sku,
            "expiry_date": p.expiry_date.isoformat(),
            "quantity": qty,
            "days_until_expiry": (p.expiry_date - today).days,
            "is_expired": p.expiry_date < today,
        }
        for p, qty in rows
    ]


@router.get("/expiring/export")
def expiring_products_export(
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    store_id: int = 1,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = expiring_products(store_id=store_id, days=days, db=db, current_user=current_user)
    return export_response(
        format,
        f"Expiring Products (next {days} days)",
        ["SKU", "Product", "Expiry Date", "Quantity", "Status"],
        [[r["sku"], r["name"], r["expiry_date"], r["quantity"], "EXPIRED" if r["is_expired"] else f"{r['days_until_expiry']}d left"] for r in rows],
    )


def _period_sales(db: Session, store_id: int, start: date, end: date | None = None):
    query = db.query(
        func.coalesce(func.sum(Order.total), 0).label("total"),
        func.count(Order.id).label("count"),
    ).filter(Order.store_id == store_id, Order.status != OrderStatus.voided, Order.created_at >= start)
    if end is not None:
        query = query.filter(Order.created_at < end)
    row = query.one()
    return float(row.total or 0), int(row.count or 0)


def _profit_breakdown(db: Session, store_id: int, start: date, end: date | None = None) -> dict:
    """
    Net Profit = (Gross Sales - Discounts - Refunds) - COGS - Expenses.

    Approximation: COGS uses each product's current `cost` field (not a historical
    cost snapshot per sale), and refund amounts include a small proportional tax
    component that isn't stripped out. Close enough for a small-shop P&L view,
    not audit-grade accounting.
    """
    order_filter = [Order.store_id == store_id, Order.status != OrderStatus.voided, Order.created_at >= start]
    if end is not None:
        order_filter.append(Order.created_at < end)

    gross_sales, discounts = (
        db.query(
            func.coalesce(func.sum(Order.subtotal), 0),
            func.coalesce(func.sum(Order.discount_total), 0),
        )
        .filter(*order_filter)
        .one()
    )

    refunds = (
        db.query(func.coalesce(func.sum(Refund.amount), 0))
        .join(Order, Order.id == Refund.order_id)
        .filter(*order_filter)
        .scalar()
    )

    cogs = (
        db.query(func.coalesce(func.sum((OrderItem.qty - OrderItem.returned_qty) * Product.cost), 0))
        .select_from(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .join(Product, Product.id == OrderItem.product_id)
        .filter(*order_filter)
        .scalar()
    )

    expense_filter = [Expense.store_id == store_id, Expense.expense_date >= start]
    if end is not None:
        expense_filter.append(Expense.expense_date < end)
    expenses = db.query(func.coalesce(func.sum(Expense.amount), 0)).filter(*expense_filter).scalar()

    gross_sales = float(gross_sales or 0)
    discounts = float(discounts or 0)
    refunds = float(refunds or 0)
    cogs = float(cogs or 0)
    expenses = float(expenses or 0)

    net_revenue = gross_sales - discounts - refunds
    gross_profit = net_revenue - cogs
    net_profit = gross_profit - expenses
    margin_pct = (net_profit / net_revenue * 100) if net_revenue else 0.0

    return {
        "gross_sales": gross_sales,
        "discounts": discounts,
        "refunds": refunds,
        "net_revenue": net_revenue,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "expenses": expenses,
        "net_profit": net_profit,
        "margin_pct": margin_pct,
    }


@router.get("/profit", dependencies=[MANAGE])
def profit_report(store_id: int = 1, days: int = 30, db: Session = Depends(get_db)):
    since = date.today() - timedelta(days=days)
    breakdown = _profit_breakdown(db, store_id, since)
    breakdown["period_days"] = days
    return breakdown


@router.get("/profit/export", dependencies=[MANAGE])
def profit_report_export(
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    store_id: int = 1,
    days: int = 30,
    db: Session = Depends(get_db),
):
    since = date.today() - timedelta(days=days)
    b = _profit_breakdown(db, store_id, since)
    rows = [
        ["Gross Sales", f"{b['gross_sales']:.2f}"],
        ["Discounts", f"-{b['discounts']:.2f}"],
        ["Refunds", f"-{b['refunds']:.2f}"],
        ["Net Revenue", f"{b['net_revenue']:.2f}"],
        ["Cost of Goods Sold", f"-{b['cogs']:.2f}"],
        ["Gross Profit", f"{b['gross_profit']:.2f}"],
        ["Expenses", f"-{b['expenses']:.2f}"],
        ["Net Profit", f"{b['net_profit']:.2f}"],
        ["Margin %", f"{b['margin_pct']:.1f}%"],
    ]
    return export_response(format, f"Profit & Loss (last {days} days)", ["Line Item", "Amount"], rows)


@router.get("/dashboard", dependencies=[MANAGE])
def dashboard(store_id: int = 1, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    today = date.today()
    yesterday = today - timedelta(days=1)
    month_start = today.replace(day=1)

    today_sales, today_count = _period_sales(db, store_id, today)
    yesterday_sales, yesterday_count = _period_sales(db, store_id, yesterday, today)
    month_sales, month_count = _period_sales(db, store_id, month_start)

    today_profit = _profit_breakdown(db, store_id, today)["net_profit"]
    month_profit = _profit_breakdown(db, store_id, month_start)["net_profit"]

    low_stock_count = (
        db.query(func.count(Inventory.id))
        .filter(Inventory.store_id == store_id, Inventory.quantity <= Inventory.reorder_level)
        .scalar()
    )

    expiring_count = len(expiring_products(store_id=store_id, days=30, db=db, current_user=current_user))

    return {
        "today_sales": today_sales,
        "today_order_count": today_count,
        "yesterday_sales": yesterday_sales,
        "yesterday_order_count": yesterday_count,
        "month_sales": month_sales,
        "month_order_count": month_count,
        "today_profit": today_profit,
        "month_profit": month_profit,
        "low_stock_count": int(low_stock_count or 0),
        "expiring_count": expiring_count,
        "top_products": top_products(store_id=store_id, days=30, limit=5, db=db, current_user=current_user),
        "daily_sales": daily_sales(store_id=store_id, days=14, db=db, current_user=current_user),
    }


@router.get("/daily-sales/export")
def daily_sales_export(
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    store_id: int = 1,
    days: int = 14,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = daily_sales(store_id=store_id, days=days, db=db, current_user=current_user)
    return export_response(
        format,
        f"Sales Report (last {days} days)",
        ["Date", "Orders", "Total"],
        [[r["day"], r["count"], f"{r['total']:.2f}"] for r in rows],
    )


@router.get("/low-stock/export")
def low_stock_report_export(
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    store_id: int = 1,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = low_stock_report(store_id=store_id, db=db, current_user=current_user)
    return export_response(
        format,
        "Low Stock Report",
        ["SKU", "Product", "Stock", "Reorder Level"],
        [[r["sku"], r["name"], r["quantity"], r["reorder_level"]] for r in rows],
    )
