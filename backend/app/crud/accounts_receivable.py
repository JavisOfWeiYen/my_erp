from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.tax import split_amount
from app.models.accounts_receivable import AccountsReceivable, ReceivableStatus
from app.models.customer import Customer
from app.models.sales_order import SalesOrder
from app.schemas.accounts_receivable import (
    ARAgingReport,
    ARAgingRow,
    AgingBuckets,
)


def _base_query():
    return select(AccountsReceivable).options(
        selectinload(AccountsReceivable.customer),
        selectinload(AccountsReceivable.sales_order),
    )


def get(db: Session, ar_id: int) -> AccountsReceivable | None:
    return db.scalar(_base_query().where(AccountsReceivable.id == ar_id))


def get_by_sales_order(db: Session, sales_order_id: int) -> AccountsReceivable | None:
    return db.scalar(
        _base_query().where(AccountsReceivable.sales_order_id == sales_order_id)
    )


def list_all(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    customer_id: int | None = None,
    status_filter: ReceivableStatus | None = None,
    issued_from: date | None = None,
    issued_to: date | None = None,
    overdue_only: bool = False,
    search: str | None = None,
) -> list[AccountsReceivable]:
    stmt = _base_query()
    if customer_id is not None:
        stmt = stmt.where(AccountsReceivable.customer_id == customer_id)
    if status_filter is not None:
        stmt = stmt.where(AccountsReceivable.status == status_filter)
    if issued_from is not None:
        stmt = stmt.where(AccountsReceivable.issued_at >= datetime.combine(issued_from, datetime.min.time(), tzinfo=timezone.utc))
    if issued_to is not None:
        stmt = stmt.where(AccountsReceivable.issued_at < datetime.combine(issued_to + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc))
    if overdue_only:
        stmt = stmt.where(
            AccountsReceivable.status.in_(
                (ReceivableStatus.open, ReceivableStatus.partial)
            ),
            AccountsReceivable.due_date < date.today(),
        )
    if search:
        stmt = stmt.where(AccountsReceivable.ar_number.ilike(f"%{search}%"))
    stmt = stmt.order_by(AccountsReceivable.id.desc()).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def generate_ar_number(db: Session, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    date_part = now.strftime("%Y%m%d")
    prefix = f"AR-{date_part}-"
    count = db.scalar(
        select(func.count(AccountsReceivable.id)).where(
            AccountsReceivable.ar_number.like(f"{prefix}%")
        )
    )
    seq = (count or 0) + 1
    return f"{prefix}{seq:04d}"


def _bucket_for(due: date, today: date) -> str:
    """Pick the aging-bucket field name for one AR row.

    Returned key matches AgingBuckets field names exactly so callers can use
    getattr/setattr without branching."""
    if due >= today:
        return "not_due"
    days = (today - due).days
    if days <= 30:
        return "d1_30"
    if days <= 60:
        return "d31_60"
    if days <= 90:
        return "d61_90"
    return "d90_plus"


def aging_report(db: Session, *, as_of: date | None = None) -> ARAgingReport:
    today = as_of or date.today()
    # Outstanding AR only: status in (open, partial), balance > 0
    stmt = (
        select(AccountsReceivable, Customer.name)
        .join(Customer, Customer.id == AccountsReceivable.customer_id)
        .where(
            AccountsReceivable.status.in_(
                (ReceivableStatus.open, ReceivableStatus.partial)
            ),
            AccountsReceivable.amount_total > AccountsReceivable.paid_amount,
        )
        .order_by(Customer.name, AccountsReceivable.due_date)
    )
    rows = db.execute(stmt).all()

    per_customer: dict[int, dict] = {}
    totals = {f: Decimal("0") for f in ("not_due", "d1_30", "d31_60", "d61_90", "d90_plus")}

    for ar, customer_name in rows:
        balance = ar.amount_total - ar.paid_amount
        bucket = _bucket_for(ar.due_date, today)
        info = per_customer.setdefault(
            ar.customer_id,
            {
                "customer_name": customer_name,
                "buckets": {f: Decimal("0") for f in totals},
            },
        )
        info["buckets"][bucket] += balance
        totals[bucket] += balance

    out_rows: list[ARAgingRow] = []
    for customer_id, info in per_customer.items():
        b = info["buckets"]
        total = sum(b.values())
        out_rows.append(
            ARAgingRow(
                customer_id=customer_id,
                customer_name=info["customer_name"],
                buckets=AgingBuckets(**b, total=total),
            )
        )
    # Sort rows by total descending so the biggest exposures float to the top.
    out_rows.sort(key=lambda r: r.buckets.total, reverse=True)

    total_sum = sum(totals.values())
    return ARAgingReport(
        as_of=today,
        rows=out_rows,
        totals=AgingBuckets(**totals, total=total_sum),
    )


def create_from_sales_order(
    db: Session, order: SalesOrder, *, issued_at: datetime, terms_days: int
) -> AccountsReceivable:
    """Build (but DO NOT commit) an AR row for a freshly-confirmed sales order.

    Caller is expected to commit as part of the confirm transaction. Returns the
    transient AR; do not access relationships until after commit + refresh.
    """
    amount_untaxed, tax_amount, amount_total = split_amount(
        order.total_amount, inclusive=order.is_tax_inclusive
    )
    ar = AccountsReceivable(
        ar_number=generate_ar_number(db, issued_at),
        sales_order_id=order.id,
        customer_id=order.customer_id,
        amount_untaxed=amount_untaxed,
        tax_amount=tax_amount,
        amount_total=amount_total,
        status=ReceivableStatus.open,
        issued_at=issued_at,
        due_date=(issued_at.date() + timedelta(days=terms_days)),
    )
    db.add(ar)
    return ar
