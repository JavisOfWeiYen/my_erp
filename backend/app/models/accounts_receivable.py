from datetime import date, datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ReceivableStatus(str, PyEnum):
    open = "open"          # nothing collected yet
    partial = "partial"    # some collected, balance > 0
    paid = "paid"          # fully collected
    voided = "voided"      # cancelled (manual)


class AccountsReceivable(Base):
    """One row per confirmed sales order. Created automatically when the order is
    confirmed, never edited directly via API — payments go through a separate flow."""

    __tablename__ = "accounts_receivable"

    id: Mapped[int] = mapped_column(primary_key=True)
    ar_number: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    # One AR per SO. UNIQUE prevents accidental duplicate creation on re-confirm.
    sales_order_id: Mapped[int] = mapped_column(
        ForeignKey("sales_orders.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
        index=True,
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    amount_untaxed: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    amount_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )

    status: Mapped[ReceivableStatus] = mapped_column(
        Enum(ReceivableStatus, name="receivable_status"),
        nullable=False,
        default=ReceivableStatus.open,
        index=True,
    )

    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    sales_order: Mapped["SalesOrder"] = relationship()  # noqa: F821
    customer: Mapped["Customer"] = relationship()  # noqa: F821
