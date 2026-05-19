from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class MarginProductRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: int
    sku: str
    name: str
    category_name: str | None
    quantity: int
    revenue: Decimal
    cost: Decimal
    gross_profit: Decimal
    margin_rate: Decimal  # 0-1 (e.g. 0.225 = 22.5%)


class MarginByProductReport(BaseModel):
    start_date: date | None
    end_date: date | None
    sort_by: str
    rows: list[MarginProductRow]
    total_revenue: Decimal
    total_cost: Decimal
    total_gross_profit: Decimal
    overall_margin_rate: Decimal


class MarginCustomerRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    customer_id: int
    customer_name: str
    order_count: int
    quantity: int
    revenue: Decimal
    cost: Decimal
    gross_profit: Decimal
    margin_rate: Decimal


class MarginByCustomerReport(BaseModel):
    start_date: date | None
    end_date: date | None
    sort_by: str
    rows: list[MarginCustomerRow]
    total_revenue: Decimal
    total_cost: Decimal
    total_gross_profit: Decimal
    overall_margin_rate: Decimal


class MarginTrendRow(BaseModel):
    year: int
    month: int
    quantity: int
    revenue: Decimal
    cost: Decimal
    gross_profit: Decimal
    margin_rate: Decimal
    # Weighted averages — useful for breakdown attribution
    # (is the margin moving because of price or cost?).
    avg_unit_price: Decimal
    avg_unit_cost: Decimal


class MarginTrendReport(BaseModel):
    months: int
    rows: list[MarginTrendRow]
