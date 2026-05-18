from decimal import Decimal

import pytest

from app.models.accounts_payable import AccountsPayable, PayableStatus
from app.models.ap_payment import APPayment

from tests.factories import make_product, make_supplier


def _create_and_receive_po(client, *, supplier_id, items, is_tax_inclusive=False):
    payload = {
        "supplier_id": supplier_id,
        "is_tax_inclusive": is_tax_inclusive,
        "items": items,
    }
    r = client.post("/api/v1/purchase-orders", json=payload)
    assert r.status_code == 201, r.text
    po = r.json()
    r2 = client.post(f"/api/v1/purchase-orders/{po['id']}/receive")
    assert r2.status_code == 200, r2.text
    return po


def _make_ap(db_session, auth, total=Decimal("100.00"), inclusive=False):
    supplier = make_supplier(db_session)
    product = make_product(db_session)
    admin = auth("admin")
    _create_and_receive_po(
        admin,
        supplier_id=supplier.id,
        is_tax_inclusive=inclusive,
        items=[{"product_id": product.id, "quantity": 1, "unit_cost": str(total)}],
    )
    db_session.expire_all()
    return db_session.query(AccountsPayable).one()


def test_full_payment_marks_paid(db_session, auth):
    ap = _make_ap(db_session, auth, total=Decimal("100.00"))  # amount_total 105

    admin = auth("admin")
    r = admin.post(
        "/api/v1/ap-payments",
        json={"accounts_payable_id": ap.id, "amount": "105.00", "method": "bank_transfer"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["payment_number"].startswith("PAY-")

    db_session.expire_all()
    ap = db_session.get(AccountsPayable, ap.id)
    assert ap.paid_amount == Decimal("105.00")
    assert ap.status == PayableStatus.paid


def test_partial_payment_marks_partial(db_session, auth):
    ap = _make_ap(db_session, auth)
    admin = auth("admin")
    admin.post("/api/v1/ap-payments", json={"accounts_payable_id": ap.id, "amount": "50.00"})

    db_session.expire_all()
    ap = db_session.get(AccountsPayable, ap.id)
    assert ap.paid_amount == Decimal("50.00")
    assert ap.status == PayableStatus.partial


def test_overpayment_rejected(db_session, auth):
    ap = _make_ap(db_session, auth)
    admin = auth("admin")
    r = admin.post("/api/v1/ap-payments", json={"accounts_payable_id": ap.id, "amount": "1000.00"})
    assert r.status_code == 400
    assert "exceeds" in r.json()["detail"].lower()
    assert db_session.query(APPayment).count() == 0


def test_payment_on_paid_ap_rejected(db_session, auth):
    ap = _make_ap(db_session, auth)
    admin = auth("admin")
    admin.post("/api/v1/ap-payments", json={"accounts_payable_id": ap.id, "amount": "105.00"})
    r = admin.post("/api/v1/ap-payments", json={"accounts_payable_id": ap.id, "amount": "1.00"})
    assert r.status_code == 409


def test_rbac_sales_cannot_record_ap_payment(db_session, auth):
    ap = _make_ap(db_session, auth)
    sales = auth("sales")
    r = sales.post("/api/v1/ap-payments", json={"accounts_payable_id": ap.id, "amount": "10.00"})
    assert r.status_code == 403


def test_rbac_warehouse_cannot_record_ap_payment(db_session, auth):
    ap = _make_ap(db_session, auth)
    wh = auth("warehouse")
    r = wh.post("/api/v1/ap-payments", json={"accounts_payable_id": ap.id, "amount": "10.00"})
    assert r.status_code == 403


def test_list_payments_for_ap(db_session, auth):
    ap = _make_ap(db_session, auth)
    admin = auth("admin")
    admin.post("/api/v1/ap-payments", json={"accounts_payable_id": ap.id, "amount": "20.00"})
    admin.post("/api/v1/ap-payments", json={"accounts_payable_id": ap.id, "amount": "30.00"})

    rs = admin.get(f"/api/v1/ap-payments?accounts_payable_id={ap.id}")
    assert rs.status_code == 200
    payments = rs.json()
    assert len(payments) == 2
