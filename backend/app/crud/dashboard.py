from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.accounts_payable import AccountsPayable, PayableStatus
from app.models.accounts_receivable import AccountsReceivable, ReceivableStatus
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

    today = date.today()
    open_ar_statuses = (ReceivableStatus.open, ReceivableStatus.partial)
    ar_balance_total = db.scalar(
        select(func.coalesce(func.sum(AccountsReceivable.amount_total - AccountsReceivable.paid_amount), 0))
        .where(AccountsReceivable.status.in_(open_ar_statuses))
    ) or Decimal("0")
    ar_overdue_balance = db.scalar(
        select(func.coalesce(func.sum(AccountsReceivable.amount_total - AccountsReceivable.paid_amount), 0))
        .where(
            and_(
                AccountsReceivable.status.in_(open_ar_statuses),
                AccountsReceivable.due_date < today,
            )
        )
    ) or Decimal("0")
    ar_overdue_count = db.scalar(
        select(func.count(AccountsReceivable.id)).where(
            and_(
                AccountsReceivable.status.in_(open_ar_statuses),
                AccountsReceivable.due_date < today,
            )
        )
    ) or 0

    open_ap_statuses = (PayableStatus.open, PayableStatus.partial)
    ap_balance_total = db.scalar(
        select(func.coalesce(func.sum(AccountsPayable.amount_total - AccountsPayable.paid_amount), 0))
        .where(AccountsPayable.status.in_(open_ap_statuses))
    ) or Decimal("0")
    ap_overdue_balance = db.scalar(
        select(func.coalesce(func.sum(AccountsPayable.amount_total - AccountsPayable.paid_amount), 0))
        .where(
            and_(
                AccountsPayable.status.in_(open_ap_statuses),
                AccountsPayable.due_date < today,
            )
        )
    ) or Decimal("0")
    ap_overdue_count = db.scalar(
        select(func.count(AccountsPayable.id)).where(
            and_(
                AccountsPayable.status.in_(open_ap_statuses),
                AccountsPayable.due_date < today,
            )
        )
    ) or 0

    return DashboardSummary(
        current_month=label,
        month_sales_amount=Decimal(month_sales).quantize(Decimal("0.01")),
        month_purchase_amount=Decimal(month_purchase).quantize(Decimal("0.01")),
        low_stock_count=int(low_stock_count),
        draft_sales_count=int(draft_sales_count),
        draft_purchases_count=int(draft_purchases_count),
        ar_balance_total=Decimal(ar_balance_total).quantize(Decimal("0.01")),
        ar_overdue_balance=Decimal(ar_overdue_balance).quantize(Decimal("0.01")),
        ar_overdue_count=int(ar_overdue_count),
        ap_balance_total=Decimal(ap_balance_total).quantize(Decimal("0.01")),
        ap_overdue_balance=Decimal(ap_overdue_balance).quantize(Decimal("0.01")),
        ap_overdue_count=int(ap_overdue_count),
    )
