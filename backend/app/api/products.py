import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_permission
from app.core.uploads import PRODUCT_IMAGES_DIR
from app.models.product import Category, Brand, Unit, Product
from app.models.inventory import Inventory
from app.models.store import Store
from app.schemas.product import (
    CategoryCreate, CategoryOut, BrandCreate, BrandOut, UnitCreate, UnitOut,
    ProductCreate, ProductUpdate, ProductOut, ProductWithStock,
)
from app.services.audit_service import log_action

ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

router = APIRouter(prefix="/products", tags=["products"])

MANAGE = Depends(require_permission("products.manage"))


# --- Categories -------------------------------------------------------

@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(Category).order_by(Category.name).all()


@router.post("/categories", response_model=CategoryOut, dependencies=[MANAGE])
def create_category(payload: CategoryCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if db.query(Category).filter(Category.name == payload.name).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Category already exists")
    category = Category(business_id=current_user.business_id, name=payload.name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


# --- Brands -------------------------------------------------------------

@router.get("/brands", response_model=list[BrandOut])
def list_brands(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(Brand).order_by(Brand.name).all()


@router.post("/brands", response_model=BrandOut, dependencies=[MANAGE])
def create_brand(payload: BrandCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if db.query(Brand).filter(Brand.name == payload.name).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Brand already exists")
    brand = Brand(business_id=current_user.business_id, name=payload.name)
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return brand


# --- Units ---------------------------------------------------------------

@router.get("/units", response_model=list[UnitOut])
def list_units(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(Unit).order_by(Unit.name).all()


@router.post("/units", response_model=UnitOut, dependencies=[MANAGE])
def create_unit(payload: UnitCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if db.query(Unit).filter(Unit.name == payload.name).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unit already exists")
    unit = Unit(business_id=current_user.business_id, name=payload.name, abbreviation=payload.abbreviation)
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


# --- Products ----------------------------------------------------------

@router.get("", response_model=list[ProductWithStock])
def list_products(
    store_id: int = 1,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Product)
    if active_only:
        query = query.filter(Product.is_active.is_(True))
    products = query.order_by(Product.name).all()

    inv_by_product = {
        inv.product_id: inv
        for inv in db.query(Inventory).filter(Inventory.store_id == store_id).all()
    }

    results = []
    for p in products:
        inv = inv_by_product.get(p.id)
        results.append(
            ProductWithStock(
                id=p.id, sku=p.sku, name=p.name, category_id=p.category_id,
                brand_id=p.brand_id, unit_id=p.unit_id,
                price=float(p.price), cost=float(p.cost), tax_rate=float(p.tax_rate),
                is_active=p.is_active, expiry_date=p.expiry_date, image_url=p.image_url,
                description=p.description, allergens=p.allergens, calories=p.calories,
                is_available_online=p.is_available_online,
                quantity=inv.quantity if inv else 0,
                reorder_level=inv.reorder_level if inv else 5,
            )
        )
    return results


@router.post("", response_model=ProductOut, dependencies=[MANAGE])
def create_product(payload: ProductCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if db.query(Product).filter(Product.sku == payload.sku).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "SKU already exists")

    data = payload.model_dump()
    initial_quantity = data.pop("initial_quantity")
    reorder_level = data.pop("reorder_level")

    product = Product(business_id=current_user.business_id, **data)
    db.add(product)
    db.flush()

    # Stock is seeded against this business's own first store — a hardcoded
    # store_id=1 (fine back when there was only ever one business) would
    # silently point a second tenant's stock at business 1's store.
    default_store_id = (
        db.query(Store.id).filter(Store.business_id == current_user.business_id).order_by(Store.id).scalar()
    )
    db.add(Inventory(
        business_id=current_user.business_id, product_id=product.id, store_id=default_store_id,
        quantity=initial_quantity, reorder_level=reorder_level,
    ))
    log_action(db, current_user.id, "create", "product", product.id, business_id=current_user.business_id)
    db.commit()
    db.refresh(product)
    return product


@router.patch("/{product_id}", response_model=ProductOut, dependencies=[MANAGE])
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    log_action(db, current_user.id, "update", "product", product.id, business_id=current_user.business_id)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[MANAGE])
def deactivate_product(product_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    product.is_active = False
    log_action(db, current_user.id, "deactivate", "product", product.id, business_id=current_user.business_id)
    db.commit()
    return None


def _delete_image_file(image_url: str | None):
    if not image_url:
        return
    path = PRODUCT_IMAGES_DIR / Path(image_url).name
    path.unlink(missing_ok=True)


@router.post("/{product_id}/image", response_model=ProductOut, dependencies=[MANAGE])
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

    ext = ALLOWED_IMAGE_TYPES.get(file.content_type)
    if ext is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Image must be JPEG, PNG, WEBP, or GIF")

    contents = await file.read()
    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Image must be smaller than 5MB")

    filename = f"{uuid.uuid4().hex}{ext}"
    (PRODUCT_IMAGES_DIR / filename).write_bytes(contents)

    _delete_image_file(product.image_url)
    product.image_url = f"/uploads/products/{filename}"
    log_action(db, current_user.id, "upload_image", "product", product.id, business_id=current_user.business_id)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}/image", response_model=ProductOut, dependencies=[MANAGE])
def delete_product_image(product_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    _delete_image_file(product.image_url)
    product.image_url = None
    log_action(db, current_user.id, "remove_image", "product", product.id, business_id=current_user.business_id)
    db.commit()
    db.refresh(product)
    return product
