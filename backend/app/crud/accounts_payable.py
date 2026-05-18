from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.tax import split_amount
from app.models.accounts_payable import AccountsPayable, PayableStatus
from app.models.purchase_order import PurchaseOrder
from app.models.supplier import Supplier
from app.schemas.accounts_payable import (
    APAgingReport,
    APAgingRow,
    AgingBuckets,
)


def _base_query():
    return select(AccountsPayable).options(
        selectinload(AccountsPayable.supplier),
        selectinload(AccountsPayable.purchase_order),
    )


def get(db: Session, ap_id: int) -> AccountsPayable | None:
    return db.scalar(_base_query().where(AccountsPayable.id == ap_id))


def get_by_purchase_order(db: Session, purchase_order_id: int) -> AccountsPayable | None:
    return db.scalar(
        _base_query().where(AccountsPayable.purchase_order_id == purchase_order_id)
    )


def list_all(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    supplier_id: int | None = None,
    status_filter: PayableStatus | None = None,
    issued_from: date | None = None,
    issued_to: date | None = None,
    overdue_only: bool = False,
    search: str | None = None,
) -> list[AccountsPayable]:
    stmt = _base_query()
    if supplier_id is not None:
        stmt = stmt.where(AccountsPayable.supplier_id == supplier_id)
    if status_filter is not None:
        stmt = stmt.where(AccountsPayable.status == status_filter)
    if issued_from is not None:
        stmt = stmt.where(AccountsPayable.issued_at >= datetime.combine(issued_from, datetime.min.time(), tzinfo=timezone.utc))
    if issued_to is not None:
        stmt = stmt.where(AccountsPayable.issued_at < datetime.combine(issued_to + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc))
    if overdue_only:
        stmt = stmt.where(
            AccountsPayable.status.in_(
                (PayableStatus.open, PayableStatus.partial)
            ),
            AccountsPayable.due_date < date.today(),
        )
    if search:
        stmt = stmt.where(AccountsPayable.ap_number.ilike(f"%{search}%"))
    stmt = stmt.order_by(AccountsPayable.id.desc()).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def generate_ap_number(db: Session, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    date_part = now.strftime("%Y%m%d")
    prefix = f"AP-{date_part}-"
    count = db.scalar(
        select(func.count(AccountsPayable.id)).where(
            AccountsPayable.ap_number.like(f"{prefix}%")
        )
    )
    seq = (count or 0) + 1
    return f"{prefix}{seq:04d}"


def _bucket_for(due: date, today: date) -> str:
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


def aging_report(db: Session, *, as_of: date | None = None) -> APAgingReport:
    today = as_of or date.today()
    stmt = (
        select(AccountsPayable, Supplier.name)
        .join(Supplier, Supplier.id == AccountsPayable.supplier_id)
        .where(
            AccountsPayable.status.in_(
                (PayableStatus.open, PayableStatus.partial)
            ),
            AccountsPayable.amount_total > AccountsPayable.paid_amount,
        )
        .order_by(Supplier.name, AccountsPayable.due_date)
    )
    rows = db.execute(stmt).all()

    per_supplier: dict[int, dict] = {}
    totals = {f: Decimal("0") for f in ("not_due", "d1_30", "d31_60", "d61_90", "d90_plus")}

    for ap, supplier_name in rows:
        balance = ap.amount_total - ap.paid_amount
        bucket = _bucket_for(ap.due_date, today)
        info = per_supplier.setdefault(
            ap.supplier_id,
            {
                "supplier_name": supplier_name,
                "buckets": {f: Decimal("0") for f in totals},
            },
        )
        info["buckets"][bucket] += balance
        totals[bucket] += balance

    out_rows: list[APAgingRow] = []
    for supplier_id, info in per_supplier.items():
        b = info["buckets"]
        total = sum(b.values())
        out_rows.append(
            APAgingRow(
                supplier_id=supplier_id,
                supplier_name=info["supplier_name"],
                buckets=AgingBuckets(**b, total=total),
            )
        )
    out_rows.sort(key=lambda r: r.buckets.total, reverse=True)

    total_sum = sum(totals.values())
    return APAgingReport(
        as_of=today,
        rows=out_rows,
        totals=AgingBuckets(**totals, total=total_sum),
    )


def create_from_purchase_order(
    db: Session, order: PurchaseOrder, *, issued_at: datetime, terms_days: int
) -> AccountsPayable:
    amount_untaxed, tax_amount, amount_total = split_amount(
        order.total_amount, inclusive=order.is_tax_inclusive
    )
    ap = AccountsPayable(
        ap_number=generate_ap_number(db, issued_at),
        purchase_order_id=order.id,
        supplier_id=order.supplier_id,
        amount_untaxed=amount_untaxed,
        tax_amount=tax_amount,
        amount_total=amount_total,
        status=PayableStatus.open,
        issued_at=issued_at,
        due_date=(issued_at.date() + timedelta(days=terms_days)),
    )
    db.add(ap)
    return ap
