"""
Creates a new tenant (business): a Business row, a default Store, and a
first admin User scoped to it. Useful for local testing without going
through the self-serve /signup page (see app/api/signup.py).

Usage:
    python -m app.create_tenant "Test Cafe" "test-cafe" [admin_email] [admin_password]

    admin_email/admin_password default to admin@{slug}.example.com / changeme123
    if omitted — fine for local testing, change them for anything real.
"""
import sys

from app.db.session import SessionLocal
from app.models import Business
from app.services.tenant_service import create_business


def run(name: str, slug: str, admin_email: str, admin_password: str):
    db = SessionLocal()
    try:
        if db.query(Business).filter(Business.slug == slug).first():
            print(f"A business with slug '{slug}' already exists.")
            return

        business, _admin = create_business(
            db, name=name, slug=slug,
            admin_name="Admin", admin_email=admin_email, admin_password=admin_password,
        )

        print(f"Created business '{name}' (slug: {slug}).")
        print(f"Staff login at /t/{slug}/ with: {admin_email} / {admin_password}")
        print(f"Public site at /t/{slug}/site/")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    name = sys.argv[1]
    slug = sys.argv[2]
    admin_email = sys.argv[3] if len(sys.argv) > 3 else f"admin@{slug}.example.com"
    admin_password = sys.argv[4] if len(sys.argv) > 4 else "changeme123"

    run(name, slug, admin_email, admin_password)
