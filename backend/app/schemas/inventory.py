from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class StockRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: int
    sku: str
    name: str
    category_id: int | None
    category_name: str | None
    unit: str
    stock_quantity: int
    low_stock_threshold: int
    is_low: bool
    is_active: bool


class MonthlyReportRow(BaseModel):
    product_id: int
    sku: str
    name: str
    category_name: str | None
    opening_stock: int
    qty_in: int          # received purchase orders
    qty_out: int         # confirmed sales orders
    adjustment: int      # signed net stock-adjustment change
    closing_stock: int
    purchase_amount: Decimal
    sales_amount: Decimal


class MonthlyReport(BaseModel):
    year: int
    month: int
    rows: list[MonthlyReportRow]
    total_purchase_amount: Decimal
    total_sales_amount: Decimal


class SalespersonReportRow(BaseModel):
    salesperson_id: int
    username: str
    full_name: str | None
    role_name: str | None
    order_count: int   # confirmed sales orders for this rep in the month
    total_qty: int     # sum of line-item quantities
    total_amount: Decimal


class SalespersonReport(BaseModel):
    year: int
    month: int
    rows: list[SalespersonReportRow]
    total_order_count: int
    total_qty: int
    total_amount: Decimal
