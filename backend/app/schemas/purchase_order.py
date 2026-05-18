from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.purchase_order import PurchaseOrderStatus


class ProductBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sku: str
    name: str


class SupplierBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class PurchaseOrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_cost: Decimal = Field(ge=Decimal("0"), max_digits=12, decimal_places=2)


class PurchaseOrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    product: ProductBrief
    quantity: int
    unit_cost: Decimal
    subtotal: Decimal


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    is_tax_inclusive: bool = False
    notes: str | None = Field(default=None, max_length=500)
    ordered_at: datetime | None = None
    items: list[PurchaseOrderItemCreate] = Field(min_length=1)


class PurchaseOrderUpdate(BaseModel):
    supplier_id: int | None = None
    is_tax_inclusive: bool | None = None
    notes: str | None = Field(default=None, max_length=500)
    ordered_at: datetime | None = None
    items: list[PurchaseOrderItemCreate] | None = Field(default=None, min_length=1)


class PurchaseOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    po_number: str
    supplier_id: int
    supplier: SupplierBrief
    status: PurchaseOrderStatus
    total_amount: Decimal
    is_tax_inclusive: bool
    notes: str | None
    ordered_at: datetime
    received_at: datetime | None
    created_by_id: int
    items: list[PurchaseOrderItemRead]
    created_at: datetime
    updated_at: datetime
