from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


def _base_query():
    return select(Product).options(selectinload(Product.category))


def get(db: Session, product_id: int) -> Product | None:
    return db.scalar(_base_query().where(Product.id == product_id))


def get_by_sku(db: Session, sku: str) -> Product | None:
    return db.scalar(_base_query().where(Product.sku == sku))


def get_by_barcode(db: Session, barcode: str) -> Product | None:
    return db.scalar(_base_query().where(Product.barcode == barcode))


def list_all(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    category_id: int | None = None,
    is_active: bool | None = None,
) -> list[Product]:
    stmt = _base_query()
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(Product.sku.ilike(like), Product.name.ilike(like), Product.barcode.ilike(like))
        )
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    if is_active is not None:
        stmt = stmt.where(Product.is_active == is_active)
    stmt = stmt.order_by(Product.id).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def create(db: Session, data: ProductCreate) -> Product:
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return get(db, product.id)


def update(db: Session, product: Product, data: ProductUpdate) -> Product:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return get(db, product.id)


def delete(db: Session, product: Product) -> None:
    db.delete(product)
    db.commit()
