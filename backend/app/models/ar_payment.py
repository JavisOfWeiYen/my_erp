from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum

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


class PaymentMethod(str, PyEnum):
    cash = "cash"               # 現金
    bank_transfer = "bank_transfer"  # 銀行轉帳
    check = "check"             # 票據
    other = "other"


class ARPayment(Base):
    """A single receipt against an Accounts Receivable. Append-only audit log."""

    __tablename__ = "ar_payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_ar_payments_amount_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_number: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    accounts_receivable_id: Mapped[int] = mapped_column(
        ForeignKey("accounts_receivable.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method"),
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

    # Void info — append-only; voided_at != null means the receipt was reversed.
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

    accounts_receivable: Mapped["AccountsReceivable"] = relationship()  # noqa: F821
    operator: Mapped["User"] = relationship(foreign_keys=[operator_id])  # noqa: F821
    voided_by: Mapped["User | None"] = relationship(foreign_keys=[voided_by_id])  # noqa: F821
