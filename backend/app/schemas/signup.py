from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserOut


class SignupRequest(BaseModel):
    business_name: str = Field(min_length=1)
    slug: str
    admin_name: str = Field(min_length=1)
    admin_email: EmailStr
    admin_password: str = Field(min_length=8)


class SignupOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    business_slug: str


class SlugAvailability(BaseModel):
    available: bool
