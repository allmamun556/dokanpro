import re
from typing import Optional

import sqlalchemy as sa
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.security import decode_access_token
from app.db.session import engine

_SLUG_PATH_RE = re.compile(r"^/t/([a-z0-9-]+)(?:/|$)")

# Slugs practically never change once a business signs up, so a simple
# process-lifetime cache (not time-based) is enough for this foundation phase.
_slug_cache: dict[str, int] = {}


def _resolve_slug(slug: str) -> Optional[int]:
    if slug in _slug_cache:
        return _slug_cache[slug]
    with engine.connect() as conn:
        row = conn.execute(sa.text("SELECT id FROM businesses WHERE slug = :slug"), {"slug": slug}).fetchone()
    if row is None:
        return None
    _slug_cache[slug] = row[0]
    return row[0]


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Resolves which tenant (business) a request belongs to and stashes it on
    request.state.business_id before any FastAPI dependency runs — including
    get_db, which needs it already set to install the per-session query
    filter (get_db is a sub-dependency of get_current_user/get_current_customer,
    so it always resolves before their bodies do; middleware is the only
    place guaranteed to run first).

    Precedence: a valid JWT's own business_id claim wins (cryptographically
    tied to the logged-in user/customer) over anything client-supplied.
    Otherwise falls back to the /t/{slug}/ path prefix (staff app + public
    site pages) or an X-Business-Slug header (API calls made from a
    /t/{slug}/ page — the API itself lives at /api/..., not under /t/{slug}/,
    so the frontend attaches the slug as a header instead).
    """

    async def dispatch(self, request: Request, call_next):
        business_id: Optional[int] = None

        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            payload = decode_access_token(auth_header[7:])
            if payload and payload.get("business_id") is not None:
                business_id = payload["business_id"]

        if business_id is None:
            match = _SLUG_PATH_RE.match(request.url.path)
            slug = match.group(1) if match else request.headers.get("x-business-slug")
            if slug:
                business_id = _resolve_slug(slug)

        request.state.business_id = business_id
        return await call_next(request)
