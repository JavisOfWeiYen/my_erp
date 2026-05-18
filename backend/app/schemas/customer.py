from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    contact_name: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=255)
    tax_id: str | None = Field(default=None, max_length=32)
    capital: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    payment_terms_days: int = Field(default=30, ge=0, le=365)
    notes: str | None = Field(default=None, max_length=500)
    is_active: bool = True


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    contact_name: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=255)
    tax_id: str | None = Field(default=None, max_length=32)
    capital: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    payment_terms_days: int | None = Field(default=None, ge=0, le=365)
    notes: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class CustomerRead(CustomerBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
