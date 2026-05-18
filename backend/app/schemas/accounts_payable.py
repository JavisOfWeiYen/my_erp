from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.accounts_payable import PayableStatus


class SupplierBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class PurchaseOrderBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    po_number: str
    received_at: datetime | None


class AccountsPayableRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ap_number: str
    purchase_order_id: int
    purchase_order: PurchaseOrderBrief
    supplier_id: int
    supplier: SupplierBrief
    amount_untaxed: Decimal
    tax_amount: Decimal
    amount_total: Decimal
    paid_amount: Decimal
    status: PayableStatus
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
        if self.status in (PayableStatus.paid, PayableStatus.voided):
            return False
        return self.balance > 0 and self.due_date < date.today()


class AgingBuckets(BaseModel):
    not_due: Decimal = Field(default=Decimal("0"))
    d1_30: Decimal = Field(default=Decimal("0"))
    d31_60: Decimal = Field(default=Decimal("0"))
    d61_90: Decimal = Field(default=Decimal("0"))
    d90_plus: Decimal = Field(default=Decimal("0"))
    total: Decimal = Field(default=Decimal("0"))


class APAgingRow(BaseModel):
    supplier_id: int
    supplier_name: str
    buckets: AgingBuckets


class APAgingReport(BaseModel):
    as_of: date
    rows: list[APAgingRow]
    totals: AgingBuckets
