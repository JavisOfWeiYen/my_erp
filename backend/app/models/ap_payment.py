from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.ar_payment import PaymentMethod  # reuse the same enum


class APPayment(Base):
    """A single payment against an Accounts Payable. Append-only audit log."""

    __tablename__ = "ap_payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_ap_payments_amount_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_number: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    accounts_payable_id: Mapped[int] = mapped_column(
        ForeignKey("accounts_payable.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method", create_type=False),
        nullable=False,
        default=PaymentMethod.bank_transfer,
    )
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    operator_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    voided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    voided_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    void_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    accounts_payable: Mapped["AccountsPayable"] = relationship()  # noqa: F821
    operator: Mapped["User"] = relationship(foreign_keys=[operator_id])  # noqa: F821
    voided_by: Mapped["User | None"] = relationship(foreign_keys=[voided_by_id])  # noqa: F821
