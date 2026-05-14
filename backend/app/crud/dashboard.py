from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.purchase_order import (
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
)
from app.models.sales_order import (
    SalesOrder,
    SalesOrderItem,
    SalesOrderStatus,
)
from app.schemas.dashboard import DashboardSummary


def _current_month_bounds(now: datetime | None = None) -> tuple[datetime, datetime, str]:
    now = now or datetime.now(timezone.utc)
    start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    if now.month == 12:
        end = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
    return start, end, f"{now.year:04d}-{now.month:02d}"


def summary(db: Session) -> DashboardSummary:
    start, end, label = _current_month_bounds()

    month_sales = db.scalar(
        select(func.coalesce(func.sum(SalesOrderItem.subtotal), 0))
        .join(SalesOrder, SalesOrder.id == SalesOrderItem.sales_order_id)
        .where(
            and_(
                SalesOrder.status == SalesOrderStatus.confirmed,
                SalesOrder.confirmed_at >= start,
                SalesOrder.confirmed_at < end,
            )
        )
    ) or Decimal("0")

    month_purchase = db.scalar(
        select(func.coalesce(func.sum(PurchaseOrderItem.subtotal), 0))
        .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderItem.purchase_order_id)
        .where(
            and_(
                PurchaseOrder.status == PurchaseOrderStatus.received,
                PurchaseOrder.received_at >= start,
                PurchaseOrder.received_at < end,
            )
        )
    ) or Decimal("0")

    low_stock_count = db.scalar(
        select(func.count(Product.id)).where(
            and_(
                Product.is_active.is_(True),
                Product.low_stock_threshold > 0,
                Product.stock_quantity <= Product.low_stock_threshold,
            )
        )
    ) or 0

    draft_sales_count = db.scalar(
        select(func.count(SalesOrder.id)).where(SalesOrder.status == SalesOrderStatus.draft)
    ) or 0

    draft_purchases_count = db.scalar(
        select(func.count(PurchaseOrder.id)).where(PurchaseOrder.status == PurchaseOrderStatus.draft)
    ) or 0

    return DashboardSummary(
        current_month=label,
        month_sales_amount=Decimal(month_sales).quantize(Decimal("0.01")),
        month_purchase_amount=Decimal(month_purchase).quantize(Decimal("0.01")),
        low_stock_count=int(low_stock_count),
        draft_sales_count=int(draft_sales_count),
        draft_purchases_count=int(draft_purchases_count),
    )
