from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.ar_payment import PaymentMethod


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    full_name: str | None


class APPaymentCreate(BaseModel):
    accounts_payable_id: int
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    method: PaymentMethod = PaymentMethod.bank_transfer
    paid_at: datetime | None = None
    reference: str | None = Field(default=None, max_length=128)
    notes: str | None = Field(default=None, max_length=500)


class APPaymentVoid(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class APPaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    payment_number: str
    accounts_payable_id: int
    amount: Decimal
    method: PaymentMethod
    paid_at: datetime
    reference: str | None
    notes: str | None
    operator_id: int
    operator: UserBrief
    voided_at: datetime | None = None
    voided_by_id: int | None = None
    voided_by: UserBrief | None = None
    void_reason: str | None = None
    created_at: datetime

    @computed_field  # type: ignore[misc]
    @property
    def is_voided(self) -> bool:
        return self.voided_at is not None
