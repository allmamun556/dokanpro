from typing import Optional
from datetime import datetime, date
from pydantic import BaseModel, EmailStr, ConfigDict

from app.models.user import RoleEnum


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: RoleEnum = RoleEnum.cashier
    phone: Optional[str] = None
    position: Optional[str] = None
    hire_date: Optional[date] = None
    salary: Optional[float] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[RoleEnum] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None
    phone: Optional[str] = None
    position: Optional[str] = None
    hire_date: Optional[date] = None
    salary: Optional[float] = None
    permission_overrides: Optional[dict[str, bool]] = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: RoleEnum
    is_active: bool
    phone: Optional[str] = None
    position: Optional[str] = None
    hire_date: Optional[date] = None
    salary: Optional[float] = None
    permission_overrides: Optional[dict[str, bool]] = None
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
