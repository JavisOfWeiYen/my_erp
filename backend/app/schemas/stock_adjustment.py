from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.stock_adjustment import StockAdjustmentReason


class ProductBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sku: str
    name: str
    unit: str


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    full_name: str | None


class StockAdjustmentCreate(BaseModel):
    product_id: int
    # Signed delta: positive = increase, negative = decrease. Must be non-zero.
    change_qty: int = Field(..., description="Signed delta; must not be 0")
    reason: StockAdjustmentReason
    notes: str | None = Field(default=None, max_length=500)


class StockAdjustmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    adjustment_number: str
    product_id: int
    product: ProductBrief
    before_qty: int
    change_qty: int
    after_qty: int
    reason: StockAdjustmentReason
    notes: str | None
    operator_id: int
    operator: UserBrief
    adjusted_at: datetime
    created_at: datetime
