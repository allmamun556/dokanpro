from typing import Optional
from pydantic import BaseModel, ConfigDict


class BusinessSettingsUpdate(BaseModel):
    business_name: Optional[str] = None
    address: Optional[str] = None
    currency_symbol: Optional[str] = None
    default_vat_rate: Optional[float] = None
    receipt_footer: Optional[str] = None


class BusinessSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    business_name: str
    address: Optional[str] = None
    currency_symbol: str
    default_vat_rate: float
    receipt_footer: Optional[str] = None


class StripeConnectStatus(BaseModel):
    connected: bool
    charges_enabled: bool


class StripeOnboardingOut(BaseModel):
    onboarding_url: str
