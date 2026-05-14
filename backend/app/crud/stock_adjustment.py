from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.product import Product
from app.models.stock_adjustment import StockAdjustment, StockAdjustmentReason
from app.schemas.stock_adjustment import StockAdjustmentCreate


def _base_query():
    return select(StockAdjustment).options(
        selectinload(StockAdjustment.product),
        selectinload(StockAdjustment.operator),
    )


def get(db: Session, adjustment_id: int) -> StockAdjustment | None:
    return db.scalar(_base_query().where(StockAdjustment.id == adjustment_id))


def list_all(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    product_id: int | None = None,
    reason: StockAdjustmentReason | None = None,
    operator_id: int | None = None,
    search: str | None = None,
) -> list[StockAdjustment]:
    stmt = _base_query()
    if product_id is not None:
        stmt = stmt.where(StockAdjustment.product_id == product_id)
    if reason is not None:
        stmt = stmt.where(StockAdjustment.reason == reason)
    if operator_id is not None:
        stmt = stmt.where(StockAdjustment.operator_id == operator_id)
    if search:
        stmt = stmt.where(
            StockAdjustment.adjustment_number.ilike(f"%{search}%")
        )
    stmt = stmt.order_by(StockAdjustment.id.desc()).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def generate_adjustment_number(db: Session, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    date_part = now.strftime("%Y%m%d")
    prefix = f"ADJ-{date_part}-"
    count = db.scalar(
        select(func.count(StockAdjustment.id)).where(
            StockAdjustment.adjustment_number.like(f"{prefix}%")
        )
    )
    seq = (count or 0) + 1
    return f"{prefix}{seq:04d}"


def create(
    db: Session, data: StockAdjustmentCreate, *, operator_id: int
) -> StockAdjustment:
    if data.change_qty == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "change_qty must not be zero")

    product = db.scalar(select(Product).where(Product.id == data.product_id))
    if not product:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Product does not exist")
    if not product.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Product is inactive")

    before_qty = product.stock_quantity or 0
    after_qty = before_qty + data.change_qty
    if after_qty < 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Adjustment would make stock negative: {before_qty} + ({data.change_qty}) = {after_qty}",
        )

    adj = StockAdjustment(
        adjustment_number=generate_adjustment_number(db),
        product_id=product.id,
        before_qty=before_qty,
        change_qty=data.change_qty,
        after_qty=after_qty,
        reason=data.reason,
        notes=data.notes,
        operator_id=operator_id,
    )
    product.stock_quantity = after_qty
    db.add(adj)
    db.commit()
    return get(db, adj.id)
