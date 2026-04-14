import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class AddressIn(BaseModel):
    street: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    country: str | None = None


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRole = UserRole.customer
    phone: str | None = Field(default=None, max_length=32)
    is_active: bool = True
    address: AddressIn | None = None


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=128)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: UserRole | None = None
    phone: str | None = Field(default=None, max_length=32)
    is_active: bool | None = None
    address: AddressIn | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    phone: str | None
    is_active: bool
    address_street: str | None
    address_city: str | None
    address_state: str | None
    address_zip_code: str | None
    address_country: str | None
    created_at: datetime
    updated_at: datetime
