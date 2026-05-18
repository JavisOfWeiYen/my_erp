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


class PayableStatus(str, PyEnum):
    open = "open"
    partial = "partial"
    paid = "paid"
    voided = "voided"


class AccountsPayable(Base):
    """One row per received purchase order. Created automatically when the order is
    received; never edited directly via API."""

    __tablename__ = "accounts_payable"

    id: Mapped[int] = mapped_column(primary_key=True)
    ap_number: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    purchase_order_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
        index=True,
    )
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    amount_untaxed: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    amount_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )

    status: Mapped[PayableStatus] = mapped_column(
        Enum(PayableStatus, name="payable_status"),
        nullable=False,
        default=PayableStatus.open,
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

    purchase_order: Mapped["PurchaseOrder"] = relationship()  # noqa: F821
    supplier: Mapped["Supplier"] = relationship()  # noqa: F821
