from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate


def get(db: Session, customer_id: int) -> Customer | None:
    return db.scalar(select(Customer).where(Customer.id == customer_id))


def get_by_name(db: Session, name: str) -> Customer | None:
    return db.scalar(select(Customer).where(Customer.name == name))


def list_all(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    is_active: bool | None = None,
) -> list[Customer]:
    stmt = select(Customer)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(
                Customer.name.ilike(like),
                Customer.contact_name.ilike(like),
                Customer.phone.ilike(like),
                Customer.tax_id.ilike(like),
            )
        )
    if is_active is not None:
        stmt = stmt.where(Customer.is_active == is_active)
    stmt = stmt.order_by(Customer.id).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def create(db: Session, data: CustomerCreate) -> Customer:
    customer = Customer(**data.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def update(db: Session, customer: Customer, data: CustomerUpdate) -> Customer:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    db.commit()
    db.refresh(customer)
    return customer


def delete(db: Session, customer: Customer) -> None:
    db.delete(customer)
    db.commit()
