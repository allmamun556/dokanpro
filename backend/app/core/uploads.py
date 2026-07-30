from pathlib import Path

# /app/uploads — a sibling of /app/frontend, backed by a named Docker volume so
# uploaded files survive image rebuilds (unlike the app code itself, which is
# copied fresh into the image every build).
UPLOADS_ROOT = Path(__file__).resolve().parent.parent.parent / "uploads"
PRODUCT_IMAGES_DIR = UPLOADS_ROOT / "products"
PRODUCT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
