from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class StockAdjustmentReason(str, PyEnum):
    # 盤盈：盤點時發現比系統紀錄多
    surplus = "surplus"
    # 盤虧：盤點時發現比系統紀錄少
    shortage = "shortage"
    # 報廢：商品損壞 / 過期 / 不堪售出
    scrap = "scrap"
    # 其他：補正、樣品、內部使用…
    other = "other"


class StockAdjustment(Base):
    """Single-row inventory adjustment (盤點 / 庫存調整).

    Each row is the immutable record of "we changed product X by +/-N because reason".
    Rows are append-only; no edits or deletes — they are the audit trail.
    Applied immediately on create (no approval workflow).
    """

    __tablename__ = "stock_adjustments"
    __table_args__ = (
        CheckConstraint("change_qty != 0", name="ck_stock_adjustments_change_nonzero"),
        CheckConstraint("after_qty >= 0", name="ck_stock_adjustments_after_qty_non_negative"),
        CheckConstraint(
            "after_qty = before_qty + change_qty",
            name="ck_stock_adjustments_qty_math",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    adjustment_number: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    before_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    change_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    after_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[StockAdjustmentReason] = mapped_column(
        Enum(StockAdjustmentReason, name="stock_adjustment_reason"),
        nullable=False,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    operator_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    adjusted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    product: Mapped["Product"] = relationship()  # noqa: F821
    operator: Mapped["User"] = relationship()  # noqa: F821
