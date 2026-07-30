import time
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.models.product import Product

MUNICH_LAT = 48.14
MUNICH_LON = 11.58

COLD_KEYWORDS = ["suppe", "soup", "stew", "eintopf", "gulasch"]
WARM_KEYWORDS = ["salat", "salad", "eis", "kalt", "cold"]
TIME_KEYWORDS = {
    "breakfast": ["fruehstueck", "frühstück", "breakfast"],
    "lunch": ["mittag", "lunch"],
    "dinner": ["abend", "dinner"],
}

_weather_cache: dict = {"bucket": None, "fetched_at": 0.0}
WEATHER_CACHE_SECONDS = 30 * 60


def _fetch_weather_bucket() -> Optional[str]:
    """Free, no-API-key weather lookup for Munich, cached in-process for 30 minutes."""
    now = time.time()
    if _weather_cache["bucket"] is not None and now - _weather_cache["fetched_at"] < WEATHER_CACHE_SECONDS:
        return _weather_cache["bucket"]

    try:
        resp = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": MUNICH_LAT, "longitude": MUNICH_LON, "current": "temperature_2m"},
            timeout=3.0,
        )
        resp.raise_for_status()
        temp = resp.json()["current"]["temperature_2m"]
    except Exception:
        return _weather_cache["bucket"]  # stale cache (possibly None) if the API is unreachable

    bucket = "cold" if temp < 12 else "warm" if temp > 22 else "mild"
    _weather_cache["bucket"] = bucket
    _weather_cache["fetched_at"] = now
    return bucket


def _time_bucket() -> str:
    hour = datetime.now(timezone.utc).hour
    if 6 <= hour < 11:
        return "breakfast"
    if 11 <= hour < 15:
        return "lunch"
    if 17 <= hour < 22:
        return "dinner"
    return "late"


def _matches_any(haystack: str, keywords: list[str]) -> bool:
    haystack = haystack.lower()
    return any(kw in haystack for kw in keywords)


def get_recommendations(db: Session, customer: Optional[Customer], limit: int = 3) -> dict:
    weather_bucket = _fetch_weather_bucket()
    time_bucket = _time_bucket()

    products = (
        db.query(Product)
        .filter(Product.is_active.is_(True), Product.is_available_online.is_(True))
        .all()
    )
    if not products:
        return {"weather": weather_bucket, "items": []}

    popularity = dict(
        db.query(OrderItem.product_id, func.count(OrderItem.id))
        .group_by(OrderItem.product_id)
        .all()
    )

    previously_ordered: set[int] = set()
    if customer is not None:
        previously_ordered = {
            row[0]
            for row in db.query(OrderItem.product_id)
            .join(Order, OrderItem.order_id == Order.id)
            .filter(Order.customer_id == customer.id)
            .distinct()
            .all()
        }

    scored = []
    for p in products:
        text = " ".join(filter(None, [p.name, p.description, p.category.name if p.category else None]))
        weather_hit = weather_bucket == "cold" and _matches_any(text, COLD_KEYWORDS)
        weather_hit = weather_hit or (weather_bucket == "warm" and _matches_any(text, WARM_KEYWORDS))
        time_hit = _matches_any(text, TIME_KEYWORDS.get(time_bucket, []))
        previous_hit = p.id in previously_ordered

        score = (
            (5 if weather_hit else 0)
            + (3 if time_hit else 0)
            + (2 if previous_hit else 0)
            + 0.1 * popularity.get(p.id, 0)
        )
        scored.append((score, weather_hit, time_hit, previous_hit, p))

    scored.sort(key=lambda row: row[0], reverse=True)
    top = scored[:limit]

    items = []
    for score, weather_hit, time_hit, previous_hit, p in top:
        if weather_hit:
            reason = f"It's {weather_bucket} today — try our {p.name}."
        elif time_hit:
            reason = f"{time_bucket.capitalize()} favorite: {p.name}."
        elif previous_hit:
            reason = f"Welcome back! You loved {p.name} last time."
        else:
            reason = f"Popular pick: {p.name}."
        items.append(
            {
                "product_id": p.id,
                "name": p.name,
                "price": float(p.price),
                "image_url": p.image_url,
                "reason": reason,
            }
        )

    return {"weather": weather_bucket, "items": items}
