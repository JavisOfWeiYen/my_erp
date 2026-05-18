from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.accounts_receivable import ReceivableStatus


class CustomerBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class SalesOrderBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    so_number: str
    confirmed_at: datetime | None


class AccountsReceivableRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ar_number: str
    sales_order_id: int
    sales_order: SalesOrderBrief
    customer_id: int
    customer: CustomerBrief
    amount_untaxed: Decimal
    tax_amount: Decimal
    amount_total: Decimal
    paid_amount: Decimal
    status: ReceivableStatus
    issued_at: datetime
    due_date: date
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[misc]
    @property
    def balance(self) -> Decimal:
        return self.amount_total - self.paid_amount

    @computed_field  # type: ignore[misc]
    @property
    def is_overdue(self) -> bool:
        if self.status in (ReceivableStatus.paid, ReceivableStatus.voided):
            return False
        return self.balance > 0 and self.due_date < date.today()


class AgingBuckets(BaseModel):
    """Outstanding balance bucketed by days past due (or not yet due)."""
    not_due: Decimal = Field(default=Decimal("0"))   # due_date >= today
    d1_30: Decimal = Field(default=Decimal("0"))     # 1-30 days overdue
    d31_60: Decimal = Field(default=Decimal("0"))    # 31-60 days overdue
    d61_90: Decimal = Field(default=Decimal("0"))    # 61-90 days overdue
    d90_plus: Decimal = Field(default=Decimal("0"))  # > 90 days overdue
    total: Decimal = Field(default=Decimal("0"))


class ARAgingRow(BaseModel):
    customer_id: int
    customer_name: str
    buckets: AgingBuckets


class ARAgingReport(BaseModel):
    as_of: date
    rows: list[ARAgingRow]
    totals: AgingBuckets
