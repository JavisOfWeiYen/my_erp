from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.crud import accounts_receivable as ar_crud
from app.models.customer import Customer
from app.models.product import Product
from app.models.sales_order import (
    SalesOrder,
    SalesOrderItem,
    SalesOrderStatus,
)
from app.models.user import User
from app.schemas.sales_order import (
    SalesOrderCreate,
    SalesOrderItemCreate,
    SalesOrderUpdate,
)


def _base_query():
    return select(SalesOrder).options(
        selectinload(SalesOrder.customer),
        selectinload(SalesOrder.salesperson),
        selectinload(SalesOrder.items).selectinload(SalesOrderItem.product),
    )


def get(db: Session, sales_order_id: int) -> SalesOrder | None:
    return db.scalar(_base_query().where(SalesOrder.id == sales_order_id))


def list_all(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    customer_id: int | None = None,
    salesperson_id: int | None = None,
    status_filter: SalesOrderStatus | None = None,
    search: str | None = None,
) -> list[SalesOrder]:
    stmt = _base_query()
    if customer_id is not None:
        stmt = stmt.where(SalesOrder.customer_id == customer_id)
    if salesperson_id is not None:
        stmt = stmt.where(SalesOrder.salesperson_id == salesperson_id)
    if status_filter is not None:
        stmt = stmt.where(SalesOrder.status == status_filter)
    if search:
        stmt = stmt.where(SalesOrder.so_number.ilike(f"%{search}%"))
    stmt = stmt.order_by(SalesOrder.id.desc()).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def generate_so_number(db: Session, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    date_part = now.strftime("%Y%m%d")
    prefix = f"SO-{date_part}-"
    count = db.scalar(
        select(func.count(SalesOrder.id)).where(
            SalesOrder.so_number.like(f"{prefix}%")
        )
    )
    seq = (count or 0) + 1
    return f"{prefix}{seq:04d}"


def _load_products_map(db: Session, product_ids: list[int]) -> dict[int, Product]:
    if not product_ids:
        return {}
    rows = db.scalars(select(Product).where(Product.id.in_(product_ids))).all()
    return {p.id: p for p in rows}


def _build_items(
    db: Session, item_payloads: list[SalesOrderItemCreate]
) -> tuple[list[SalesOrderItem], Decimal]:
    product_ids = [it.product_id for it in item_payloads]
    products = _load_products_map(db, product_ids)
    missing = [pid for pid in product_ids if pid not in products]
    if missing:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Product(s) not found: {missing}",
        )
    items: list[SalesOrderItem] = []
    total = Decimal("0")
    for payload in item_payloads:
        subtotal = (payload.unit_price * payload.quantity).quantize(Decimal("0.01"))
        items.append(
            SalesOrderItem(
                product_id=payload.product_id,
                quantity=payload.quantity,
                unit_price=payload.unit_price,
                subtotal=subtotal,
            )
        )
        total += subtotal
    return items, total.quantize(Decimal("0.01"))


def _check_salesperson(db: Session, salesperson_id: int) -> User:
    user = db.scalar(select(User).where(User.id == salesperson_id))
    if not user:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Salesperson does not exist"
        )
    if not user.is_active:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Salesperson is inactive"
        )
    return user


def create_draft(
    db: Session,
    data: SalesOrderCreate,
    *,
    customer: Customer,
    created_by_id: int,
) -> SalesOrder:
    _check_salesperson(db, data.salesperson_id)
    items, total = _build_items(db, data.items)
    order = SalesOrder(
        so_number=generate_so_number(db),
        customer_id=customer.id,
        salesperson_id=data.salesperson_id,
        status=SalesOrderStatus.draft,
        total_amount=total,
        is_tax_inclusive=data.is_tax_inclusive,
        notes=data.notes,
        ordered_at=data.ordered_at or datetime.now(timezone.utc),
        created_by_id=created_by_id,
        items=items,
    )
    db.add(order)
    db.commit()
    return get(db, order.id)


def update_draft(
    db: Session,
    order: SalesOrder,
    data: SalesOrderUpdate,
    *,
    customer: Customer | None,
) -> SalesOrder:
    if order.status != SalesOrderStatus.draft:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Only draft sales orders can be updated",
        )
    if customer is not None:
        order.customer_id = customer.id
    if data.salesperson_id is not None and data.salesperson_id != order.salesperson_id:
        _check_salesperson(db, data.salesperson_id)
        order.salesperson_id = data.salesperson_id
    if data.is_tax_inclusive is not None:
        order.is_tax_inclusive = data.is_tax_inclusive
    if data.notes is not None:
        order.notes = data.notes
    if data.ordered_at is not None:
        order.ordered_at = data.ordered_at
    if data.items is not None:
        order.items.clear()
        db.flush()
        items, total = _build_items(db, data.items)
        order.items = items
        order.total_amount = total
    db.commit()
    return get(db, order.id)


def cancel(db: Session, order: SalesOrder) -> SalesOrder:
    if order.status != SalesOrderStatus.draft:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Only draft sales orders can be cancelled",
        )
    order.status = SalesOrderStatus.cancelled
    db.commit()
    return get(db, order.id)


def confirm(db: Session, order: SalesOrder) -> SalesOrder:
    if order.status != SalesOrderStatus.draft:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Only draft sales orders can be confirmed",
        )
    if not order.items:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot confirm a sales order with no items",
        )
    product_ids = [it.product_id for it in order.items]
    products = _load_products_map(db, product_ids)
    missing = [pid for pid in product_ids if pid not in products]
    if missing:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Product(s) no longer exist: {missing}",
        )
    needed: dict[int, int] = {}
    for item in order.items:
        needed[item.product_id] = needed.get(item.product_id, 0) + item.quantity
    shortages = []
    for pid, qty in needed.items():
        product = products[pid]
        on_hand = product.stock_quantity or 0
        if on_hand < qty:
            shortages.append(
                f"{product.sku} ({product.name}): need {qty}, on-hand {on_hand}"
            )
    if shortages:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Insufficient stock: " + "; ".join(shortages),
        )
    for item in order.items:
        product = products[item.product_id]
        product.stock_quantity = (product.stock_quantity or 0) - item.quantity
        # Snapshot cost at confirm time — frozen for the lifetime of this line.
        item.unit_cost = product.cost_price
    order.status = SalesOrderStatus.confirmed
    order.confirmed_at = datetime.now(timezone.utc)
    # Auto-create the receivable in the same transaction.
    ar_crud.create_from_sales_order(
        db,
        order,
        issued_at=order.confirmed_at,
        terms_days=order.customer.payment_terms_days,
    )
    db.commit()
    return get(db, order.id)
