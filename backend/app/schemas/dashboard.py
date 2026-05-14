from decimal import Decimal

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    current_month: str  # YYYY-MM
    month_sales_amount: Decimal
    month_purchase_amount: Decimal
    low_stock_count: int
    draft_sales_count: int
    draft_purchases_count: int
