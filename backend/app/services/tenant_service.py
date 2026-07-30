from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Business, Store, User, RoleEnum


def create_business(
    db: Session,
    *,
    name: str,
    slug: str,
    admin_name: str,
    admin_email: str,
    admin_password: str,
) -> tuple[Business, User]:
    """
    Creates a new tenant: a Business row, a default Store, and a first admin
    User scoped to it. Shared by the create_tenant.py management script and
    the self-serve signup endpoint (app/api/signup.py) so there's one
    implementation of "what a brand-new business looks like".
    """
    business = Business(name=name, slug=slug)
    db.add(business)
    db.flush()

    store = Store(business_id=business.id, name=f"{name} — Main Store")
    db.add(store)

    admin = User(
        business_id=business.id,
        name=admin_name,
        email=admin_email,
        password_hash=hash_password(admin_password),
        role=RoleEnum.admin,
    )
    db.add(admin)

    db.commit()
    db.refresh(business)
    db.refresh(admin)
    return business, admin
