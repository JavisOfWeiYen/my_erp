from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierUpdate


def get(db: Session, supplier_id: int) -> Supplier | None:
    return db.scalar(select(Supplier).where(Supplier.id == supplier_id))


def get_by_name(db: Session, name: str) -> Supplier | None:
    return db.scalar(select(Supplier).where(Supplier.name == name))


def list_all(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    is_active: bool | None = None,
) -> list[Supplier]:
    stmt = select(Supplier)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(
                Supplier.name.ilike(like),
                Supplier.contact_name.ilike(like),
                Supplier.phone.ilike(like),
                Supplier.tax_id.ilike(like),
            )
        )
    if is_active is not None:
        stmt = stmt.where(Supplier.is_active == is_active)
    stmt = stmt.order_by(Supplier.id).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def create(db: Session, data: SupplierCreate) -> Supplier:
    supplier = Supplier(**data.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


def update(db: Session, supplier: Supplier, data: SupplierUpdate) -> Supplier:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(supplier, field, value)
    db.commit()
    db.refresh(supplier)
    return supplier


def delete(db: Session, supplier: Supplier) -> None:
    db.delete(supplier)
    db.commit()
