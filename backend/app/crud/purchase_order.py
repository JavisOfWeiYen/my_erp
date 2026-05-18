from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.crud import accounts_payable as ap_crud
from app.models.product import Product
from app.models.purchase_order import (
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
)
from app.models.supplier import Supplier
from app.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderItemCreate,
    PurchaseOrderUpdate,
)


def _base_query():
    return select(PurchaseOrder).options(
        selectinload(PurchaseOrder.supplier),
        selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.product),
    )


def get(db: Session, purchase_order_id: int) -> PurchaseOrder | None:
    return db.scalar(_base_query().where(PurchaseOrder.id == purchase_order_id))


def list_all(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    supplier_id: int | None = None,
    status_filter: PurchaseOrderStatus | None = None,
    search: str | None = None,
) -> list[PurchaseOrder]:
    stmt = _base_query()
    if supplier_id is not None:
        stmt = stmt.where(PurchaseOrder.supplier_id == supplier_id)
    if status_filter is not None:
        stmt = stmt.where(PurchaseOrder.status == status_filter)
    if search:
        stmt = stmt.where(PurchaseOrder.po_number.ilike(f"%{search}%"))
    stmt = stmt.order_by(PurchaseOrder.id.desc()).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def generate_po_number(db: Session, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    date_part = now.strftime("%Y%m%d")
    prefix = f"PO-{date_part}-"
    count = db.scalar(
        select(func.count(PurchaseOrder.id)).where(
            PurchaseOrder.po_number.like(f"{prefix}%")
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
    db: Session, item_payloads: list[PurchaseOrderItemCreate]
) -> tuple[list[PurchaseOrderItem], Decimal]:
    product_ids = [it.product_id for it in item_payloads]
    products = _load_products_map(db, product_ids)
    missing = [pid for pid in product_ids if pid not in products]
    if missing:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Product(s) not found: {missing}",
        )
    items: list[PurchaseOrderItem] = []
    total = Decimal("0")
    for payload in item_payloads:
        subtotal = (payload.unit_cost * payload.quantity).quantize(Decimal("0.01"))
        items.append(
            PurchaseOrderItem(
                product_id=payload.product_id,
                quantity=payload.quantity,
                unit_cost=payload.unit_cost,
                subtotal=subtotal,
            )
        )
        total += subtotal
    return items, total.quantize(Decimal("0.01"))


def create_draft(
    db: Session,
    data: PurchaseOrderCreate,
    *,
    supplier: Supplier,
    created_by_id: int,
) -> PurchaseOrder:
    items, total = _build_items(db, data.items)
    order = PurchaseOrder(
        po_number=generate_po_number(db),
        supplier_id=supplier.id,
        status=PurchaseOrderStatus.draft,
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
    order: PurchaseOrder,
    data: PurchaseOrderUpdate,
    *,
    supplier: Supplier | None,
) -> PurchaseOrder:
    if order.status != PurchaseOrderStatus.draft:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Only draft purchase orders can be updated",
        )
    if supplier is not None:
        order.supplier_id = supplier.id
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


def cancel(db: Session, order: PurchaseOrder) -> PurchaseOrder:
    if order.status != PurchaseOrderStatus.draft:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Only draft purchase orders can be cancelled",
        )
    order.status = PurchaseOrderStatus.cancelled
    db.commit()
    return get(db, order.id)


def receive(db: Session, order: PurchaseOrder) -> PurchaseOrder:
    if order.status != PurchaseOrderStatus.draft:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Only draft purchase orders can be received",
        )
    if not order.items:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot receive a purchase order with no items",
        )
    product_ids = [it.product_id for it in order.items]
    products = _load_products_map(db, product_ids)
    missing = [pid for pid in product_ids if pid not in products]
    if missing:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Product(s) no longer exist: {missing}",
        )
    for item in order.items:
        product = products[item.product_id]
        product.stock_quantity = (product.stock_quantity or 0) + item.quantity
        product.cost_price = item.unit_cost
    order.status = PurchaseOrderStatus.received
    order.received_at = datetime.now(timezone.utc)
    # Auto-create the payable in the same transaction.
    ap_crud.create_from_purchase_order(
        db,
        order,
        issued_at=order.received_at,
        terms_days=order.supplier.payment_terms_days,
    )
    db.commit()
    return get(db, order.id)
