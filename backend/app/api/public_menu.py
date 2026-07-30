from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import require_tenant
from app.db.session import get_db
from app.models.product import Category, Product
from app.models.review import Review
from app.schemas.public_menu import PublicMenuCategory, PublicMenuItem

router = APIRouter(prefix="/menu", tags=["public-menu"], dependencies=[Depends(require_tenant)])


def _rating_stats(db: Session) -> dict[int, tuple[float, int]]:
    rows = (
        db.query(Review.product_id, func.avg(Review.rating), func.count(Review.id))
        .group_by(Review.product_id)
        .all()
    )
    return {product_id: (float(avg), count) for product_id, avg, count in rows}


def _to_item(product: Product, rating_stats: dict[int, tuple[float, int]]) -> PublicMenuItem:
    avg_rating, review_count = rating_stats.get(product.id, (None, 0))
    item = PublicMenuItem.model_validate(product)
    item.avg_rating = round(avg_rating, 1) if avg_rating is not None else None
    item.review_count = review_count
    return item


@router.get("", response_model=list[PublicMenuCategory])
def get_menu(db: Session = Depends(get_db)):
    products = (
        db.query(Product)
        .filter(Product.is_active.is_(True), Product.is_available_online.is_(True))
        .order_by(Product.name)
        .all()
    )
    categories = db.query(Category).order_by(Category.name).all()
    rating_stats = _rating_stats(db)

    items_by_category: dict[int | None, list[PublicMenuItem]] = {}
    for p in products:
        items_by_category.setdefault(p.category_id, []).append(_to_item(p, rating_stats))

    menu = [
        PublicMenuCategory(id=c.id, name=c.name, items=items_by_category.get(c.id, []))
        for c in categories
        if items_by_category.get(c.id)
    ]

    # Products without a category would otherwise silently disappear from the
    # public menu — surface them under an "Other" bucket instead.
    uncategorized = items_by_category.get(None)
    if uncategorized:
        menu.append(PublicMenuCategory(id=0, name="Other", items=uncategorized))

    return menu


@router.get("/products/{product_id}", response_model=PublicMenuItem)
def get_menu_item(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None or not product.is_active or not product.is_available_online:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return _to_item(product, _rating_stats(db))
