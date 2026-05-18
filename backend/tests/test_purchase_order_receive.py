from decimal import Decimal

import pytest

from app.models.product import Product
from app.models.purchase_order import PurchaseOrder, PurchaseOrderStatus

from tests.factories import make_product, make_supplier


def _create_draft(client, supplier_id, items):
    payload = {"supplier_id": supplier_id, "items": items}
    r = client.post("/api/v1/purchase-orders", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def test_receive_adds_stock_and_updates_cost(db_session, auth):
    supplier = make_supplier(db_session)
    product = make_product(db_session, stock=5, cost=Decimal("10.00"))

    admin = auth("admin")
    po = _create_draft(
        admin,
        supplier.id,
        [{"product_id": product.id, "quantity": 12, "unit_cost": "25.50"}],
    )

    warehouse = auth("warehouse")
    r = warehouse.post(f"/api/v1/purchase-orders/{po['id']}/receive")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "received"
    assert body["received_at"] is not None

    db_session.expire_all()
    p = db_session.get(Product, product.id)
    assert p.stock_quantity == 5 + 12
    assert p.cost_price == Decimal("25.50")


def test_receive_multi_item_updates_each_product(db_session, auth):
    supplier = make_supplier(db_session)
    a = make_product(db_session, sku="A", name="A", stock=0, cost=Decimal("1.00"))
    b = make_product(db_session, sku="B", name="B", stock=3, cost=Decimal("2.00"))

    admin = auth("admin")
    po = _create_draft(
        admin,
        supplier.id,
        [
            {"product_id": a.id, "quantity": 10, "unit_cost": "5.00"},
            {"product_id": b.id, "quantity": 4, "unit_cost": "7.50"},
        ],
    )

    r = admin.post(f"/api/v1/purchase-orders/{po['id']}/receive")
    assert r.status_code == 200, r.text

    db_session.expire_all()
    pa = db_session.get(Product, a.id)
    pb = db_session.get(Product, b.id)
    assert pa.stock_quantity == 10
    assert pa.cost_price == Decimal("5.00")
    assert pb.stock_quantity == 7
    assert pb.cost_price == Decimal("7.50")


@pytest.mark.parametrize(
    "first_action,expected_status",
    [("receive", "received"), ("cancel", "cancelled")],
)
def test_only_draft_can_be_received(db_session, auth, first_action, expected_status):
    supplier = make_supplier(db_session)
    product = make_product(db_session)

    admin = auth("admin")
    po = _create_draft(
        admin,
        supplier.id,
        [{"product_id": product.id, "quantity": 1, "unit_cost": "1.00"}],
    )

    r1 = admin.post(f"/api/v1/purchase-orders/{po['id']}/{first_action}")
    assert r1.status_code == 200, r1.text
    assert r1.json()["status"] == expected_status

    r2 = admin.post(f"/api/v1/purchase-orders/{po['id']}/receive")
    assert r2.status_code == 409
    assert "draft" in r2.json()["detail"].lower()


def test_receive_with_no_items_rejected(db_session, auth, users):
    # The create schema requires min_length=1 items, so build a draft directly in the DB
    # to exercise the receive() empty-items guard.
    supplier = make_supplier(db_session)
    order = PurchaseOrder(
        po_number="PO-EMPTY-0001",
        supplier_id=supplier.id,
        status=PurchaseOrderStatus.draft,
        total_amount=Decimal("0"),
        created_by_id=users["admin"].id,
    )
    db_session.add(order)
    db_session.commit()

    admin = auth("admin")
    r = admin.post(f"/api/v1/purchase-orders/{order.id}/receive")
    assert r.status_code == 400
    assert "no items" in r.json()["detail"].lower()


def test_receive_rbac(db_session, auth):
    supplier = make_supplier(db_session)
    product = make_product(db_session)

    admin = auth("admin")
    po = _create_draft(
        admin,
        supplier.id,
        [{"product_id": product.id, "quantity": 1, "unit_cost": "1.00"}],
    )

    # sales cannot receive
    sales = auth("sales")
    r = sales.post(f"/api/v1/purchase-orders/{po['id']}/receive")
    assert r.status_code == 403

    # warehouse can
    warehouse = auth("warehouse")
    r = warehouse.post(f"/api/v1/purchase-orders/{po['id']}/receive")
    assert r.status_code == 200


def test_receive_requires_auth(client, db_session, auth):
    supplier = make_supplier(db_session)
    product = make_product(db_session)

    admin = auth("admin")
    po = _create_draft(
        admin,
        supplier.id,
        [{"product_id": product.id, "quantity": 1, "unit_cost": "1.00"}],
    )

    # bare client (no Authorization header)
    r = client.post(f"/api/v1/purchase-orders/{po['id']}/receive")
    assert r.status_code == 401
