from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.category import CategoryRead


class ProductBase(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    barcode: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=500)
    unit: str = Field(default="個", min_length=1, max_length=16)
    unit_price: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), max_digits=12, decimal_places=2)
    cost_price: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), max_digits=12, decimal_places=2)
    low_stock_threshold: int = Field(default=0, ge=0)
    is_active: bool = True
    category_id: int | None = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=128)
    barcode: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=500)
    unit: str | None = Field(default=None, min_length=1, max_length=16)
    unit_price: Decimal | None = Field(default=None, ge=Decimal("0"), max_digits=12, decimal_places=2)
    cost_price: Decimal | None = Field(default=None, ge=Decimal("0"), max_digits=12, decimal_places=2)
    low_stock_threshold: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    category_id: int | None = None


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    stock_quantity: int
    category: CategoryRead | None = None
    created_at: datetime
    updated_at: datetime
