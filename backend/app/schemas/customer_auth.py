from typing import Optional
from pydantic import BaseModel, EmailStr

from app.schemas.customer import CustomerOut


class CustomerRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None


class CustomerToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    customer: CustomerOut
