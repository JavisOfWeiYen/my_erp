from calendar import monthrange
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.product import Product
from app.models.purchase_order import (
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
)
from app.models.role import Role
from app.models.sales_order import (
    SalesOrder,
    SalesOrderItem,
    SalesOrderStatus,
)
from app.models.stock_adjustment import StockAdjustment
from app.models.user import User
from app.schemas.inventory import (
    MonthlyReport,
    MonthlyReportRow,
    SalespersonReport,
    SalespersonReportRow,
    StockRow,
)


def list_stock(
    db: Session,
    *,
    search: str | None = None,
    category_id: int | None = None,
    low_only: bool = False,
    include_inactive: bool = False,
) -> list[StockRow]:
    stmt = select(Product).options(selectinload(Product.category))
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(Product.sku.ilike(like), Product.name.ilike(like)))
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    if not include_inactive:
        stmt = stmt.where(Product.is_active.is_(True))
    stmt = stmt.order_by(Product.sku)
    products = list(db.scalars(stmt))

    rows: list[StockRow] = []
    for p in products:
        is_low = p.low_stock_threshold > 0 and p.stock_quantity <= p.low_stock_threshold
        if low_only and not is_low:
            continue
        rows.append(
            StockRow(
                product_id=p.id,
                sku=p.sku,
                name=p.name,
                category_id=p.category_id,
                category_name=p.category.name if p.category else None,
                unit=p.unit,
                stock_quantity=p.stock_quantity,
                low_stock_threshold=p.low_stock_threshold,
                is_low=is_low,
                is_active=p.is_active,
            )
        )
    return rows


def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    last_day = monthrange(year, month)[1]
    # next-month boundary, half-open [start, end)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    _ = last_day  # noqa: F841
    return start, end


def monthly_report(db: Session, *, year: int, month: int) -> MonthlyReport:
    if not (1 <= month <= 12):
        raise ValueError("month must be between 1 and 12")
    start, end = _month_bounds(year, month)

    products = list(
        db.scalars(
            select(Product)
            .options(selectinload(Product.category))
            .order_by(Product.sku)
        )
    )

    # In-month received purchase orders: quantity + amount per product
    in_rows = db.execute(
        select(
            PurchaseOrderItem.product_id,
            func.coalesce(func.sum(PurchaseOrderItem.quantity), 0).label("qty"),
            func.coalesce(func.sum(PurchaseOrderItem.subtotal), 0).label("amount"),
        )
        .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderItem.purchase_order_id)
        .where(
            and_(
                PurchaseOrder.status == PurchaseOrderStatus.received,
                PurchaseOrder.received_at >= start,
                PurchaseOrder.received_at < end,
            )
        )
        .group_by(PurchaseOrderItem.product_id)
    ).all()
    in_by_pid = {pid: (int(qty), Decimal(amount)) for pid, qty, amount in in_rows}

    # In-month confirmed sales orders
    out_rows = db.execute(
        select(
            SalesOrderItem.product_id,
            func.coalesce(func.sum(SalesOrderItem.quantity), 0).label("qty"),
            func.coalesce(func.sum(SalesOrderItem.subtotal), 0).label("amount"),
        )
        .join(SalesOrder, SalesOrder.id == SalesOrderItem.sales_order_id)
        .where(
            and_(
                SalesOrder.status == SalesOrderStatus.confirmed,
                SalesOrder.confirmed_at >= start,
                SalesOrder.confirmed_at < end,
            )
        )
        .group_by(SalesOrderItem.product_id)
    ).all()
    out_by_pid = {pid: (int(qty), Decimal(amount)) for pid, qty, amount in out_rows}

    # Net moves AFTER month-end (used to roll the current stock back to closing_stock)
    after_in_rows = db.execute(
        select(
            PurchaseOrderItem.product_id,
            func.coalesce(func.sum(PurchaseOrderItem.quantity), 0),
        )
        .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderItem.purchase_order_id)
        .where(
            and_(
                PurchaseOrder.status == PurchaseOrderStatus.received,
                PurchaseOrder.received_at >= end,
            )
        )
        .group_by(PurchaseOrderItem.product_id)
    ).all()
    after_in = {pid: int(qty) for pid, qty in after_in_rows}

    after_out_rows = db.execute(
        select(
            SalesOrderItem.product_id,
            func.coalesce(func.sum(SalesOrderItem.quantity), 0),
        )
        .join(SalesOrder, SalesOrder.id == SalesOrderItem.sales_order_id)
        .where(
            and_(
                SalesOrder.status == SalesOrderStatus.confirmed,
                SalesOrder.confirmed_at >= end,
            )
        )
        .group_by(SalesOrderItem.product_id)
    ).all()
    after_out = {pid: int(qty) for pid, qty in after_out_rows}

    # Stock adjustments: signed net per product, in-month + after-month
    adj_in_rows = db.execute(
        select(
            StockAdjustment.product_id,
            func.coalesce(func.sum(StockAdjustment.change_qty), 0),
        )
        .where(
            and_(
                StockAdjustment.adjusted_at >= start,
                StockAdjustment.adjusted_at < end,
            )
        )
        .group_by(StockAdjustment.product_id)
    ).all()
    adj_in = {pid: int(net) for pid, net in adj_in_rows}

    adj_after_rows = db.execute(
        select(
            StockAdjustment.product_id,
            func.coalesce(func.sum(StockAdjustment.change_qty), 0),
        )
        .where(StockAdjustment.adjusted_at >= end)
        .group_by(StockAdjustment.product_id)
    ).all()
    adj_after = {pid: int(net) for pid, net in adj_after_rows}

    rows: list[MonthlyReportRow] = []
    total_purchase = Decimal("0")
    total_sales = Decimal("0")
    for p in products:
        qty_in, amount_in = in_by_pid.get(p.id, (0, Decimal("0")))
        qty_out, amount_out = out_by_pid.get(p.id, (0, Decimal("0")))
        adj_net = adj_in.get(p.id, 0)
        # closing_stock = current_stock - (moves after month-end), where moves include
        # received purchases (add), confirmed sales (subtract), and adjustments (signed).
        closing = (
            (p.stock_quantity or 0)
            - after_in.get(p.id, 0)
            + after_out.get(p.id, 0)
            - adj_after.get(p.id, 0)
        )
        opening = closing - qty_in + qty_out - adj_net
        rows.append(
            MonthlyReportRow(
                product_id=p.id,
                sku=p.sku,
                name=p.name,
                category_name=p.category.name if p.category else None,
                opening_stock=opening,
                qty_in=qty_in,
                qty_out=qty_out,
                adjustment=adj_net,
                closing_stock=closing,
                purchase_amount=amount_in.quantize(Decimal("0.01")),
                sales_amount=amount_out.quantize(Decimal("0.01")),
            )
        )
        total_purchase += amount_in
        total_sales += amount_out

    return MonthlyReport(
        year=year,
        month=month,
        rows=rows,
        total_purchase_amount=total_purchase.quantize(Decimal("0.01")),
        total_sales_amount=total_sales.quantize(Decimal("0.01")),
    )


def salesperson_monthly_report(
    db: Session, *, year: int, month: int
) -> SalespersonReport:
    if not (1 <= month <= 12):
        raise ValueError("month must be between 1 and 12")
    start, end = _month_bounds(year, month)

    # Aggregate over confirmed sales orders in [start, end).
    agg_rows = db.execute(
        select(
            SalesOrder.salesperson_id,
            func.count(func.distinct(SalesOrder.id)).label("order_count"),
            func.coalesce(func.sum(SalesOrderItem.quantity), 0).label("qty"),
            func.coalesce(func.sum(SalesOrderItem.subtotal), 0).label("amount"),
        )
        .join(SalesOrderItem, SalesOrderItem.sales_order_id == SalesOrder.id)
        .where(
            and_(
                SalesOrder.status == SalesOrderStatus.confirmed,
                SalesOrder.confirmed_at >= start,
                SalesOrder.confirmed_at < end,
            )
        )
        .group_by(SalesOrder.salesperson_id)
    ).all()

    if not agg_rows:
        return SalespersonReport(
            year=year,
            month=month,
            rows=[],
            total_order_count=0,
            total_qty=0,
            total_amount=Decimal("0.00"),
        )

    salesperson_ids = [r[0] for r in agg_rows]
    user_rows = db.execute(
        select(User, Role)
        .join(Role, Role.id == User.role_id)
        .where(User.id.in_(salesperson_ids))
    ).all()
    user_by_id = {u.id: (u, r) for u, r in user_rows}

    rows: list[SalespersonReportRow] = []
    total_orders = 0
    total_qty = 0
    total_amount = Decimal("0")
    for sp_id, order_count, qty, amount in agg_rows:
        user_role = user_by_id.get(sp_id)
        if user_role is None:
            # Salesperson row exists but the user record is gone — shouldn't happen
            # under RESTRICT, but be defensive.
            username, full_name, role_name = f"#{sp_id}", None, None
        else:
            u, r = user_role
            username, full_name, role_name = u.username, u.full_name, r.name
        amt_dec = Decimal(amount).quantize(Decimal("0.01"))
        rows.append(
            SalespersonReportRow(
                salesperson_id=sp_id,
                username=username,
                full_name=full_name,
                role_name=role_name,
                order_count=int(order_count),
                total_qty=int(qty),
                total_amount=amt_dec,
            )
        )
        total_orders += int(order_count)
        total_qty += int(qty)
        total_amount += amt_dec

    # Sort by total_amount desc — top performer first.
    rows.sort(key=lambda r: r.total_amount, reverse=True)

    return SalespersonReport(
        year=year,
        month=month,
        rows=rows,
        total_order_count=total_orders,
        total_qty=total_qty,
        total_amount=total_amount.quantize(Decimal("0.01")),
    )
