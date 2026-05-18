from decimal import Decimal

from app.models.customer import Customer
from app.models.product import Product
from app.models.supplier import Supplier


def make_supplier(db, name="Supplier A", is_active=True):
    s = Supplier(name=name, is_active=is_active)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def make_customer(db, name="Customer A", is_active=True):
    c = Customer(name=name, is_active=is_active)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def make_product(
    db,
    sku="SKU-001",
    name="Widget",
    stock=0,
    cost=Decimal("0"),
    price=Decimal("100"),
    is_active=True,
):
    p = Product(
        sku=sku,
        name=name,
        unit="個",
        unit_price=price,
        cost_price=cost,
        stock_quantity=stock,
        is_active=is_active,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p
