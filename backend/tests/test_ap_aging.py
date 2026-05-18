from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models.accounts_payable import AccountsPayable

from tests.factories import make_product, make_supplier


def _receive_po(client, supplier, product, unit_cost="100.00"):
    po = client.post(
        "/api/v1/purchase-orders",
        json={
            "supplier_id": supplier.id,
            "items": [{"product_id": product.id, "quantity": 1, "unit_cost": unit_cost}],
        },
    ).json()
    client.post(f"/api/v1/purchase-orders/{po['id']}/receive")
    return po


def _set_ap_due(db_session, purchase_order_id, due_date):
    ap = db_session.query(AccountsPayable).filter_by(purchase_order_id=purchase_order_id).one()
    ap.due_date = due_date
    db_session.commit()
    return ap


def test_ap_aging_buckets(db_session, auth):
    supplier = make_supplier(db_session, name="S1")
    today = date.today()

    admin = auth("admin")
    pos = []
    for i in range(5):
        p = make_product(db_session, sku=f"AP-{i}", name=f"p{i}")
        pos.append(_receive_po(admin, supplier, p))

    _set_ap_due(db_session, pos[0]["id"], today + timedelta(days=5))    # not_due
    _set_ap_due(db_session, pos[1]["id"], today - timedelta(days=15))   # d1_30
    _set_ap_due(db_session, pos[2]["id"], today - timedelta(days=45))   # d31_60
    _set_ap_due(db_session, pos[3]["id"], today - timedelta(days=80))   # d61_90
    _set_ap_due(db_session, pos[4]["id"], today - timedelta(days=120))  # d90_plus

    r = admin.get("/api/v1/accounts-payable/aging")
    assert r.status_code == 200
    body = r.json()
    assert len(body["rows"]) == 1
    b = body["rows"][0]["buckets"]
    assert Decimal(b["not_due"]) == Decimal("105.00")
    assert Decimal(b["d1_30"]) == Decimal("105.00")
    assert Decimal(b["d31_60"]) == Decimal("105.00")
    assert Decimal(b["d61_90"]) == Decimal("105.00")
    assert Decimal(b["d90_plus"]) == Decimal("105.00")
    assert Decimal(b["total"]) == Decimal("525.00")


def test_paid_ap_excluded(db_session, auth):
    supplier = make_supplier(db_session)
    product = make_product(db_session)
    admin = auth("admin")
    po = _receive_po(admin, supplier, product)
    ap_id = db_session.query(AccountsPayable).filter_by(purchase_order_id=po["id"]).one().id
    admin.post("/api/v1/ap-payments", json={"accounts_payable_id": ap_id, "amount": "105.00"})

    r = admin.get("/api/v1/accounts-payable/aging")
    assert r.json()["rows"] == []


def test_ap_aging_groups_by_supplier(db_session, auth):
    a = make_supplier(db_session, name="Alpha")
    b = make_supplier(db_session, name="Beta")
    admin = auth("admin")
    p1 = make_product(db_session, sku="X1")
    p2 = make_product(db_session, sku="X2")
    p3 = make_product(db_session, sku="X3")
    _receive_po(admin, a, p1, unit_cost="100.00")
    _receive_po(admin, b, p2, unit_cost="100.00")
    _receive_po(admin, b, p3, unit_cost="200.00")

    r = admin.get("/api/v1/accounts-payable/aging")
    rows = r.json()["rows"]
    assert len(rows) == 2
    # Beta total 315 > Alpha 105 → sorted desc
    assert rows[0]["supplier_name"] == "Beta"
    assert Decimal(rows[0]["buckets"]["total"]) == Decimal("315.00")
    assert rows[1]["supplier_name"] == "Alpha"
