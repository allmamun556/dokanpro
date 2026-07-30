from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://pos_user:pos_password@localhost:5432/pos_db"
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    # Same-origin app (this service serves its own frontend) — no cross-origin
    # caller exists today. Empty by default rather than "*", since "*" combined
    # with allow_credentials=True makes the CORS middleware reflect any Origin
    # header, which is unnecessary attack surface with zero functional upside.
    CORS_ORIGINS: List[str] = []

    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    PUBLIC_SITE_URL: str = "http://localhost:8000"

    # Stripe Connect (Standard) — diner payments routed to each business's own account.
    STRIPE_CONNECT_WEBHOOK_SECRET: str = ""

    # Stripe Subscriptions — businesses paying the platform, on the platform's own account.
    STRIPE_SUBSCRIPTION_PRICE_ID: str = ""

    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = "onboarding@resend.dev"

    class Config:
        env_file = ".env"


settings = Settings()
