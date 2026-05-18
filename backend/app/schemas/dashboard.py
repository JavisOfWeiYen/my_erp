from decimal import Decimal

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    current_month: str  # YYYY-MM
    month_sales_amount: Decimal
    month_purchase_amount: Decimal
    low_stock_count: int
    draft_sales_count: int
    draft_purchases_count: int
    # AR/AP exposure — only open+partial are counted; paid/voided excluded.
    ar_balance_total: Decimal
    ar_overdue_balance: Decimal
    ar_overdue_count: int
    ap_balance_total: Decimal
    ap_overdue_balance: Decimal
    ap_overdue_count: int
