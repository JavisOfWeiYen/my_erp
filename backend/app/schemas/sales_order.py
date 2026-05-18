from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.sales_order import SalesOrderStatus


class ProductBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sku: str
    name: str


class CustomerBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    full_name: str | None


class SalesOrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=Decimal("0"), max_digits=12, decimal_places=2)


class SalesOrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    product: ProductBrief
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class SalesOrderCreate(BaseModel):
    customer_id: int
    salesperson_id: int
    is_tax_inclusive: bool = False
    notes: str | None = Field(default=None, max_length=500)
    ordered_at: datetime | None = None
    items: list[SalesOrderItemCreate] = Field(min_length=1)


class SalesOrderUpdate(BaseModel):
    customer_id: int | None = None
    salesperson_id: int | None = None
    is_tax_inclusive: bool | None = None
    notes: str | None = Field(default=None, max_length=500)
    ordered_at: datetime | None = None
    items: list[SalesOrderItemCreate] | None = Field(default=None, min_length=1)


class SalesOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    so_number: str
    customer_id: int
    customer: CustomerBrief
    salesperson_id: int
    salesperson: UserBrief
    status: SalesOrderStatus
    total_amount: Decimal
    is_tax_inclusive: bool
    notes: str | None
    ordered_at: datetime
    confirmed_at: datetime | None
    created_by_id: int
    items: list[SalesOrderItemRead]
    created_at: datetime
    updated_at: datetime
