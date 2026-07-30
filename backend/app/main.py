import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.uploads import UPLOADS_ROOT
from app.core.tenant_middleware import TenantMiddleware
from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from app.db.session import SessionLocal
from app.models.business import Business
from app.services import ws_manager
from app.api import (
    auth, users, products, inventory, orders, reports, customers, discounts,
    suppliers, purchases, stores, transfers, expenses, settings as settings_api, held_sales,
    reservations, reviews, newsletter, notifications, ws, signup, billing,
    customer_auth, public_menu, public_checkout, public_reservations, public_account, public_discounts,
    public_reviews, public_newsletter, public_tables, public_recommendations,
)

app = FastAPI(title="DokanPro API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


@app.on_event("startup")
async def _capture_event_loop():
    ws_manager.set_event_loop(asyncio.get_running_loop())

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TenantMiddleware)
app.add_middleware(SlowAPIMiddleware)

app.include_router(signup.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(inventory.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(customers.router, prefix="/api")
app.include_router(discounts.router, prefix="/api")
app.include_router(suppliers.router, prefix="/api")
app.include_router(purchases.router, prefix="/api")
app.include_router(stores.router, prefix="/api")
app.include_router(transfers.router, prefix="/api")
app.include_router(expenses.router, prefix="/api")
app.include_router(settings_api.router, prefix="/api")
app.include_router(held_sales.router, prefix="/api")
app.include_router(reservations.router, prefix="/api")
app.include_router(reviews.router, prefix="/api")
app.include_router(newsletter.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(ws.router)

# Customer-facing (public) API — separate auth, no staff JWT/permissions involved.
app.include_router(customer_auth.router, prefix="/api/public")
app.include_router(public_menu.router, prefix="/api/public")
app.include_router(public_checkout.router, prefix="/api/public")
app.include_router(public_checkout.webhook_router, prefix="/api/public")
app.include_router(public_reservations.router, prefix="/api/public")
app.include_router(public_account.router, prefix="/api/public")
app.include_router(public_discounts.router, prefix="/api/public")
app.include_router(public_reviews.router, prefix="/api/public")
app.include_router(public_newsletter.router, prefix="/api/public")
app.include_router(public_tables.router, prefix="/api/public")
app.include_router(public_recommendations.router, prefix="/api/public")


@app.get("/api/health")
def health():
    return {"status": "ok"}


# --- Serve the frontend (so the whole app runs from a single process) ---
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
    app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
    app.mount("/uploads", StaticFiles(directory=UPLOADS_ROOT), name="uploads")

    @app.get("/")
    def root():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/{page_name}.html")
    def page(page_name: str):
        candidate = FRONTEND_DIR / f"{page_name}.html"
        if candidate.exists():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIR / "index.html")

    # Multi-tenant staff entry points — same static files as above (the
    # frontend is shared code, not per-tenant data), just reachable under a
    # /t/{slug}/ prefix so the browser's URL carries the tenant. Staff pages
    # link to each other with relative hrefs, so once logged in via one of
    # these, ordinary navigation stays under the same prefix automatically.
    @app.get("/t/{slug}/")
    def root_tenant(slug: str):
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/t/{slug}/{page_name}.html")
    def page_tenant(slug: str, page_name: str):
        candidate = FRONTEND_DIR / f"{page_name}.html"
        if candidate.exists():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIR / "index.html")


# --- Serve the customer-facing restaurant site (Phase 1) ---
SITE_DIR = FRONTEND_DIR / "site"

if SITE_DIR.exists():
    app.mount("/site/css", StaticFiles(directory=SITE_DIR / "css"), name="site-css")
    app.mount("/site/js", StaticFiles(directory=SITE_DIR / "js"), name="site-js")
    app.mount("/site/icons", StaticFiles(directory=SITE_DIR / "icons"), name="site-icons")

    @app.get("/site")
    def site_root():
        return FileResponse(SITE_DIR / "index.html")

    @app.get("/site/manifest.json")
    def site_manifest():
        return FileResponse(SITE_DIR / "manifest.json", media_type="application/manifest+json")

    @app.get("/site/sw.js")
    def site_service_worker():
        # Served from /site/ (not /site/js/) so its default scope covers the
        # whole customer site, matching the "customer site only" PWA decision.
        return FileResponse(SITE_DIR / "sw.js", media_type="application/javascript")

    @app.get("/site/{page_name}.html")
    def site_page(page_name: str):
        candidate = SITE_DIR / f"{page_name}.html"
        if candidate.exists():
            return FileResponse(candidate)
        # Don't fall back to the staff app's index.html for a bad customer-site URL.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Page not found")

    # Multi-tenant customer site entry points — mirrors the /site/* routes
    # above at a /t/{slug}/site/... prefix. sw.js needs its own route here
    # (not just a redirect) because a service worker's registration URL
    # determines its default scope — the customer site's JS registers it
    # with a path relative to the current page, so this must physically
    # exist for that page's scope to end up as /t/{slug}/site/ instead of
    # bleeding into every tenant.
    @app.get("/t/{slug}/site")
    def site_root_tenant(slug: str):
        return FileResponse(SITE_DIR / "index.html")

    @app.get("/t/{slug}/site/manifest.json")
    def site_manifest_tenant(slug: str):
        # The static manifest.json's start_url/scope point at the unprefixed
        # /site/ — fine for the single-tenant fallback above, wrong here: it
        # would launch an installed PWA into the wrong tenant. Rebuild it
        # per-tenant instead of just serving the same static file.
        db = SessionLocal()
        try:
            business = db.query(Business).filter(Business.slug == slug).first()
        finally:
            db.close()
        if business is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Business not found")

        manifest = json.loads((SITE_DIR / "manifest.json").read_text())
        manifest["name"] = business.name
        manifest["short_name"] = business.name[:30]
        manifest["description"] = f"Order online, reserve a table, and browse the menu of {business.name}."
        manifest["start_url"] = f"/t/{slug}/site/index.html"
        manifest["scope"] = f"/t/{slug}/site/"
        return JSONResponse(content=manifest, media_type="application/manifest+json")

    @app.get("/t/{slug}/site/sw.js")
    def site_service_worker_tenant(slug: str):
        return FileResponse(SITE_DIR / "sw.js", media_type="application/javascript")

    @app.get("/t/{slug}/site/{page_name}.html")
    def site_page_tenant(slug: str, page_name: str):
        candidate = SITE_DIR / f"{page_name}.html"
        if candidate.exists():
            return FileResponse(candidate)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Page not found")
