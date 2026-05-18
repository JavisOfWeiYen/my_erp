from decimal import Decimal

import pytest

from app.models.product import Product
from app.models.sales_order import SalesOrder, SalesOrderStatus

from tests.factories import make_customer, make_product


def _create_draft(client, customer_id, salesperson_id, items):
    payload = {
        "customer_id": customer_id,
        "salesperson_id": salesperson_id,
        "items": items,
    }
    r = client.post("/api/v1/sales-orders", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def test_confirm_decrements_stock_and_sets_timestamp(db_session, auth, users):
    customer = make_customer(db_session)
    product = make_product(db_session, stock=20, cost=Decimal("10.00"), price=Decimal("50.00"))

    sales = auth("sales")
    so = _create_draft(
        sales,
        customer.id,
        users["sales"].id,
        [{"product_id": product.id, "quantity": 7, "unit_price": "50.00"}],
    )
    assert so["confirmed_at"] is None

    r = sales.post(f"/api/v1/sales-orders/{so['id']}/confirm")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "confirmed"
    assert body["confirmed_at"] is not None

    db_session.expire_all()
    p = db_session.get(Product, product.id)
    assert p.stock_quantity == 20 - 7
    # product.unit_price MUST NOT be written back from the order
    assert p.unit_price == Decimal("50.00")
    assert p.cost_price == Decimal("10.00")


def test_confirm_insufficient_stock_rejected_no_changes(db_session, auth, users):
    customer = make_customer(db_session)
    product = make_product(db_session, stock=3, price=Decimal("50.00"))

    sales = auth("sales")
    so = _create_draft(
        sales,
        customer.id,
        users["sales"].id,
        [{"product_id": product.id, "quantity": 10, "unit_price": "50.00"}],
    )

    r = sales.post(f"/api/v1/sales-orders/{so['id']}/confirm")
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert "insufficient stock" in detail.lower()
    assert "need 10" in detail
    assert "on-hand 3" in detail

    db_session.expire_all()
    p = db_session.get(Product, product.id)
    assert p.stock_quantity == 3  # unchanged

    # order stays draft, no confirmed_at
    refetched = db_session.get(SalesOrder, so["id"])
    assert refetched.status == SalesOrderStatus.draft
    assert refetched.confirmed_at is None


def test_confirm_is_atomic_when_one_item_short(db_session, auth, users):
    customer = make_customer(db_session)
    ok = make_product(db_session, sku="OK", name="OK", stock=100, price=Decimal("10.00"))
    short = make_product(db_session, sku="SHORT", name="Short", stock=1, price=Decimal("10.00"))

    sales = auth("sales")
    so = _create_draft(
        sales,
        customer.id,
        users["sales"].id,
        [
            {"product_id": ok.id, "quantity": 5, "unit_price": "10.00"},
            {"product_id": short.id, "quantity": 5, "unit_price": "10.00"},
        ],
    )

    r = sales.post(f"/api/v1/sales-orders/{so['id']}/confirm")
    assert r.status_code == 400

    db_session.expire_all()
    # Neither product is decremented — atomicity must hold.
    assert db_session.get(Product, ok.id).stock_quantity == 100
    assert db_session.get(Product, short.id).stock_quantity == 1


def test_confirm_aggregates_repeated_lines_for_same_product(db_session, auth, users):
    """Two lines on the same product should be summed when checking stock."""
    customer = make_customer(db_session)
    product = make_product(db_session, stock=8, price=Decimal("10.00"))

    sales = auth("sales")
    so = _create_draft(
        sales,
        customer.id,
        users["sales"].id,
        [
            {"product_id": product.id, "quantity": 5, "unit_price": "10.00"},
            {"product_id": product.id, "quantity": 5, "unit_price": "10.00"},
        ],
    )

    # 10 needed, only 8 on-hand — must be rejected.
    r = sales.post(f"/api/v1/sales-orders/{so['id']}/confirm")
    assert r.status_code == 400
    assert "need 10" in r.json()["detail"]


@pytest.mark.parametrize(
    "first_action,expected_status",
    [("confirm", "confirmed"), ("cancel", "cancelled")],
)
def test_only_draft_can_be_confirmed(db_session, auth, users, first_action, expected_status):
    customer = make_customer(db_session)
    product = make_product(db_session, stock=10, price=Decimal("10.00"))

    sales = auth("sales")
    so = _create_draft(
        sales,
        customer.id,
        users["sales"].id,
        [{"product_id": product.id, "quantity": 1, "unit_price": "10.00"}],
    )

    r1 = sales.post(f"/api/v1/sales-orders/{so['id']}/{first_action}")
    assert r1.status_code == 200
    assert r1.json()["status"] == expected_status

    r2 = sales.post(f"/api/v1/sales-orders/{so['id']}/confirm")
    assert r2.status_code == 409
    assert "draft" in r2.json()["detail"].lower()


def test_confirm_rbac(db_session, auth, users):
    customer = make_customer(db_session)
    product = make_product(db_session, stock=10, price=Decimal("10.00"))

    sales = auth("sales")
    so = _create_draft(
        sales,
        customer.id,
        users["sales"].id,
        [{"product_id": product.id, "quantity": 1, "unit_price": "10.00"}],
    )

    # warehouse cannot confirm sales
    warehouse = auth("warehouse")
    r = warehouse.post(f"/api/v1/sales-orders/{so['id']}/confirm")
    assert r.status_code == 403

    # manager can
    manager = auth("manager")
    r = manager.post(f"/api/v1/sales-orders/{so['id']}/confirm")
    assert r.status_code == 200
