"""Analytics CRUD — margin (gross profit) reports.

Margin = revenue - cost.
  revenue = sum(unit_price * quantity)
  cost    = sum(COALESCE(unit_cost, 0) * quantity)

Tax handling: revenue numbers are taken as-is from sales_order_items.subtotal,
matching the rest of the reporting layer (monthly_report does not split tax
either). Cost is always tax-free (cost_price has no tax notion). Demo-scope
trade-off; a future refinement can strip tax based on order.is_tax_inclusive.

Only ``confirmed`` sales orders contribute. Draft / cancelled rows are excluded.
"""
from calendar import monthrange
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.customer import Customer
from app.models.product import Product
from app.models.sales_order import SalesOrder, SalesOrderItem, SalesOrderStatus
from app.schemas.analytics import (
    MarginByCustomerReport,
    MarginByProductReport,
    MarginCustomerRow,
    MarginProductRow,
    MarginTrendReport,
    MarginTrendRow,
)

TWO_DP = Decimal("0.01")
FOUR_DP = Decimal("0.0001")


_SORT_KEYS_PRODUCT = {"margin_rate", "revenue", "gross_profit", "quantity"}
_SORT_KEYS_CUSTOMER = {"margin_rate", "revenue", "gross_profit"}


def _safe_rate(profit: Decimal, revenue: Decimal) -> Decimal:
    if revenue <= 0:
        return Decimal("0.0000")
    return (profit / revenue).quantize(FOUR_DP)


def _date_range(
    start_date: date | None, end_date: date | None
) -> tuple[datetime | None, datetime | None]:
    start_dt = (
        datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
        if start_date
        else None
    )
    # end_date is inclusive on the calling side; convert to half-open by +1 day.
    if end_date:
        # Push to next-day 00:00 UTC.
        y, m, d = end_date.year, end_date.month, end_date.day
        last_day = monthrange(y, m)[1]
        if d < last_day:
            end_dt = datetime(y, m, d + 1, tzinfo=timezone.utc)
        elif m < 12:
            end_dt = datetime(y, m + 1, 1, tzinfo=timezone.utc)
        else:
            end_dt = datetime(y + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end_dt = None
    return start_dt, end_dt


def _confirmed_filter(start_dt: datetime | None, end_dt: datetime | None):
    conds = [SalesOrder.status == SalesOrderStatus.confirmed]
    if start_dt is not None:
        conds.append(SalesOrder.confirmed_at >= start_dt)
    if end_dt is not None:
        conds.append(SalesOrder.confirmed_at < end_dt)
    return and_(*conds)


def margin_by_product(
    db: Session,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    sort_by: str = "margin_rate",
    top: int = 50,
) -> MarginByProductReport:
    if sort_by not in _SORT_KEYS_PRODUCT:
        raise ValueError(f"sort_by must be one of {sorted(_SORT_KEYS_PRODUCT)}")
    if top <= 0:
        raise ValueError("top must be > 0")

    start_dt, end_dt = _date_range(start_date, end_date)

    rev_expr = func.sum(SalesOrderItem.unit_price * SalesOrderItem.quantity)
    cost_expr = func.sum(
        func.coalesce(SalesOrderItem.unit_cost, 0) * SalesOrderItem.quantity
    )
    qty_expr = func.sum(SalesOrderItem.quantity)

    agg = db.execute(
        select(
            SalesOrderItem.product_id,
            func.coalesce(qty_expr, 0).label("qty"),
            func.coalesce(rev_expr, 0).label("revenue"),
            func.coalesce(cost_expr, 0).label("cost"),
        )
        .join(SalesOrder, SalesOrder.id == SalesOrderItem.sales_order_id)
        .where(_confirmed_filter(start_dt, end_dt))
        .group_by(SalesOrderItem.product_id)
    ).all()

    if not agg:
        return MarginByProductReport(
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            rows=[],
            total_revenue=Decimal("0.00"),
            total_cost=Decimal("0.00"),
            total_gross_profit=Decimal("0.00"),
            overall_margin_rate=Decimal("0.0000"),
        )

    product_ids = [r[0] for r in agg]
    product_rows = db.execute(
        select(Product, Category)
        .join(Category, Category.id == Product.category_id, isouter=True)
        .where(Product.id.in_(product_ids))
    ).all()
    product_map = {p.id: (p, c) for p, c in product_rows}

    rows: list[MarginProductRow] = []
    total_revenue = Decimal("0")
    total_cost = Decimal("0")
    for pid, qty, revenue, cost in agg:
        revenue = Decimal(revenue or 0)
        cost = Decimal(cost or 0)
        gp = revenue - cost
        entry = product_map.get(pid)
        if entry is None:
            sku = f"#{pid}"
            name = f"Product {pid}"
            cat_name = None
        else:
            p, c = entry
            sku, name = p.sku, p.name
            cat_name = c.name if c is not None else None
        rows.append(
            MarginProductRow(
                product_id=pid,
                sku=sku,
                name=name,
                category_name=cat_name,
                quantity=int(qty),
                revenue=revenue.quantize(TWO_DP),
                cost=cost.quantize(TWO_DP),
                gross_profit=gp.quantize(TWO_DP),
                margin_rate=_safe_rate(gp, revenue),
            )
        )
        total_revenue += revenue
        total_cost += cost

    sort_key_fn = {
        "margin_rate": lambda r: r.margin_rate,
        "revenue": lambda r: r.revenue,
        "gross_profit": lambda r: r.gross_profit,
        "quantity": lambda r: r.quantity,
    }[sort_by]
    rows.sort(key=sort_key_fn, reverse=True)
    rows = rows[:top]

    total_gp = total_revenue - total_cost
    return MarginByProductReport(
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        rows=rows,
        total_revenue=total_revenue.quantize(TWO_DP),
        total_cost=total_cost.quantize(TWO_DP),
        total_gross_profit=total_gp.quantize(TWO_DP),
        overall_margin_rate=_safe_rate(total_gp, total_revenue),
    )


def margin_by_customer(
    db: Session,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    sort_by: str = "margin_rate",
    top: int = 50,
) -> MarginByCustomerReport:
    if sort_by not in _SORT_KEYS_CUSTOMER:
        raise ValueError(f"sort_by must be one of {sorted(_SORT_KEYS_CUSTOMER)}")
    if top <= 0:
        raise ValueError("top must be > 0")

    start_dt, end_dt = _date_range(start_date, end_date)

    rev_expr = func.sum(SalesOrderItem.unit_price * SalesOrderItem.quantity)
    cost_expr = func.sum(
        func.coalesce(SalesOrderItem.unit_cost, 0) * SalesOrderItem.quantity
    )
    qty_expr = func.sum(SalesOrderItem.quantity)
    order_count_expr = func.count(func.distinct(SalesOrder.id))

    agg = db.execute(
        select(
            SalesOrder.customer_id,
            func.coalesce(order_count_expr, 0).label("order_count"),
            func.coalesce(qty_expr, 0).label("qty"),
            func.coalesce(rev_expr, 0).label("revenue"),
            func.coalesce(cost_expr, 0).label("cost"),
        )
        .join(SalesOrderItem, SalesOrderItem.sales_order_id == SalesOrder.id)
        .where(_confirmed_filter(start_dt, end_dt))
        .group_by(SalesOrder.customer_id)
    ).all()

    if not agg:
        return MarginByCustomerReport(
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            rows=[],
            total_revenue=Decimal("0.00"),
            total_cost=Decimal("0.00"),
            total_gross_profit=Decimal("0.00"),
            overall_margin_rate=Decimal("0.0000"),
        )

    customer_ids = [r[0] for r in agg]
    customer_rows = db.execute(
        select(Customer).where(Customer.id.in_(customer_ids))
    ).all()
    customer_map = {c[0].id: c[0] for c in customer_rows}

    rows: list[MarginCustomerRow] = []
    total_revenue = Decimal("0")
    total_cost = Decimal("0")
    for cid, oc, qty, revenue, cost in agg:
        revenue = Decimal(revenue or 0)
        cost = Decimal(cost or 0)
        gp = revenue - cost
        c = customer_map.get(cid)
        rows.append(
            MarginCustomerRow(
                customer_id=cid,
                customer_name=c.name if c else f"Customer {cid}",
                order_count=int(oc),
                quantity=int(qty),
                revenue=revenue.quantize(TWO_DP),
                cost=cost.quantize(TWO_DP),
                gross_profit=gp.quantize(TWO_DP),
                margin_rate=_safe_rate(gp, revenue),
            )
        )
        total_revenue += revenue
        total_cost += cost

    sort_key_fn = {
        "margin_rate": lambda r: r.margin_rate,
        "revenue": lambda r: r.revenue,
        "gross_profit": lambda r: r.gross_profit,
    }[sort_by]
    rows.sort(key=sort_key_fn, reverse=True)
    rows = rows[:top]

    total_gp = total_revenue - total_cost
    return MarginByCustomerReport(
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        rows=rows,
        total_revenue=total_revenue.quantize(TWO_DP),
        total_cost=total_cost.quantize(TWO_DP),
        total_gross_profit=total_gp.quantize(TWO_DP),
        overall_margin_rate=_safe_rate(total_gp, total_revenue),
    )


def _prev_month(y: int, m: int) -> tuple[int, int]:
    if m == 1:
        return y - 1, 12
    return y, m - 1


def margin_trend(db: Session, *, months: int = 12) -> MarginTrendReport:
    if not (1 <= months <= 60):
        raise ValueError("months must be between 1 and 60")

    today = datetime.now(timezone.utc)
    # Build the window of (year, month) buckets ending with the current month.
    buckets: list[tuple[int, int]] = []
    y, m = today.year, today.month
    for _ in range(months):
        buckets.append((y, m))
        y, m = _prev_month(y, m)
    buckets.reverse()

    earliest_year, earliest_month = buckets[0]
    start_dt = datetime(earliest_year, earliest_month, 1, tzinfo=timezone.utc)
    # end is the start of the month after the last bucket.
    last_y, last_m = buckets[-1]
    if last_m == 12:
        end_dt = datetime(last_y + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end_dt = datetime(last_y, last_m + 1, 1, tzinfo=timezone.utc)

    # Aggregate per (year, month) bucket via Python — avoids portability headaches
    # with date_trunc / strftime variants across SQLite / PG / MySQL.
    item_rows = db.execute(
        select(
            SalesOrder.confirmed_at,
            SalesOrderItem.quantity,
            SalesOrderItem.unit_price,
            SalesOrderItem.unit_cost,
        )
        .join(SalesOrderItem, SalesOrderItem.sales_order_id == SalesOrder.id)
        .where(
            and_(
                SalesOrder.status == SalesOrderStatus.confirmed,
                SalesOrder.confirmed_at >= start_dt,
                SalesOrder.confirmed_at < end_dt,
            )
        )
    ).all()

    agg: dict[tuple[int, int], dict[str, Decimal]] = {
        b: {
            "qty": Decimal("0"),
            "revenue": Decimal("0"),
            "cost": Decimal("0"),
        }
        for b in buckets
    }
    for confirmed_at, qty, unit_price, unit_cost in item_rows:
        if confirmed_at is None:
            continue
        key = (confirmed_at.year, confirmed_at.month)
        if key not in agg:
            continue
        qty_d = Decimal(qty)
        price_d = Decimal(unit_price)
        cost_d = Decimal(unit_cost) if unit_cost is not None else Decimal("0")
        agg[key]["qty"] += qty_d
        agg[key]["revenue"] += price_d * qty_d
        agg[key]["cost"] += cost_d * qty_d

    rows: list[MarginTrendRow] = []
    for (yr, mo) in buckets:
        a = agg[(yr, mo)]
        qty = a["qty"]
        revenue = a["revenue"]
        cost = a["cost"]
        gp = revenue - cost
        if qty > 0:
            avg_price = (revenue / qty).quantize(TWO_DP)
            avg_cost = (cost / qty).quantize(TWO_DP)
        else:
            avg_price = Decimal("0.00")
            avg_cost = Decimal("0.00")
        rows.append(
            MarginTrendRow(
                year=yr,
                month=mo,
                quantity=int(qty),
                revenue=revenue.quantize(TWO_DP),
                cost=cost.quantize(TWO_DP),
                gross_profit=gp.quantize(TWO_DP),
                margin_rate=_safe_rate(gp, revenue),
                avg_unit_price=avg_price,
                avg_unit_cost=avg_cost,
            )
        )

    return MarginTrendReport(months=months, rows=rows)
