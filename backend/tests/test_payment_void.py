"""Voiding receipts/payments reverses their effect on AR/AP totals + status,
while keeping the payment row visible (audit trail)."""
from decimal import Decimal

import pytest

from app.models.accounts_payable import AccountsPayable, PayableStatus
from app.models.accounts_receivable import AccountsReceivable, ReceivableStatus
from app.models.ap_payment import APPayment
from app.models.ar_payment import ARPayment

from tests.factories import make_customer, make_product, make_supplier


# ---------------------- AR helpers ----------------------

def _confirm_so(client, customer_id, salesperson_id, product_id, unit_price="100.00"):
    so = client.post(
        "/api/v1/sales-orders",
        json={
            "customer_id": customer_id,
            "salesperson_id": salesperson_id,
            "items": [{"product_id": product_id, "quantity": 1, "unit_price": unit_price}],
        },
    ).json()
    client.post(f"/api/v1/sales-orders/{so['id']}/confirm")
    return so


def _make_ar(db_session, auth, users):
    customer = make_customer(db_session)
    product = make_product(db_session, stock=100)
    sales = auth("sales")
    _confirm_so(sales, customer.id, users["sales"].id, product.id)  # 105 total
    db_session.expire_all()
    return db_session.query(AccountsReceivable).one()


# ---------------------- AR void tests ----------------------

def test_void_only_payment_returns_ar_to_open(db_session, auth, users):
    ar = _make_ar(db_session, auth, users)
    sales = auth("sales")
    rp = sales.post(
        "/api/v1/ar-payments",
        json={"accounts_receivable_id": ar.id, "amount": "105.00"},
    )
    pid = rp.json()["id"]

    r = sales.post(f"/api/v1/ar-payments/{pid}/void", json={"reason": "wrong customer"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["is_voided"] is True
    assert body["void_reason"] == "wrong customer"
    assert body["voided_at"] is not None
    assert body["voided_by_id"] == users["sales"].id

    db_session.expire_all()
    ar = db_session.get(AccountsReceivable, ar.id)
    assert ar.paid_amount == Decimal("0")
    assert ar.status == ReceivableStatus.open


def test_void_one_of_two_payments_makes_ar_partial(db_session, auth, users):
    ar = _make_ar(db_session, auth, users)
    sales = auth("sales")
    p1 = sales.post(
        "/api/v1/ar-payments",
        json={"accounts_receivable_id": ar.id, "amount": "60.00"},
    ).json()
    p2 = sales.post(
        "/api/v1/ar-payments",
        json={"accounts_receivable_id": ar.id, "amount": "45.00"},
    ).json()
    db_session.expire_all()
    assert db_session.get(AccountsReceivable, ar.id).status == ReceivableStatus.paid

    sales.post(f"/api/v1/ar-payments/{p1['id']}/void", json={})

    db_session.expire_all()
    ar = db_session.get(AccountsReceivable, ar.id)
    assert ar.paid_amount == Decimal("45.00")
    assert ar.status == ReceivableStatus.partial


def test_voided_payment_still_listed(db_session, auth, users):
    """Audit trail: voided rows must remain visible in list output."""
    ar = _make_ar(db_session, auth, users)
    sales = auth("sales")
    p = sales.post(
        "/api/v1/ar-payments",
        json={"accounts_receivable_id": ar.id, "amount": "30.00"},
    ).json()
    sales.post(f"/api/v1/ar-payments/{p['id']}/void", json={"reason": "duplicate"})

    rs = sales.get(f"/api/v1/ar-payments?accounts_receivable_id={ar.id}").json()
    assert len(rs) == 1
    assert rs[0]["is_voided"] is True
    assert rs[0]["void_reason"] == "duplicate"


def test_cannot_void_already_voided_payment(db_session, auth, users):
    ar = _make_ar(db_session, auth, users)
    sales = auth("sales")
    p = sales.post(
        "/api/v1/ar-payments",
        json={"accounts_receivable_id": ar.id, "amount": "30.00"},
    ).json()
    assert sales.post(f"/api/v1/ar-payments/{p['id']}/void", json={}).status_code == 200
    r2 = sales.post(f"/api/v1/ar-payments/{p['id']}/void", json={})
    assert r2.status_code == 409
    assert "already voided" in r2.json()["detail"].lower()


def test_void_unknown_payment_404(db_session, auth):
    r = auth("sales").post("/api/v1/ar-payments/99999/void", json={})
    assert r.status_code == 404


def test_void_rbac_warehouse_blocked_on_ar(db_session, auth, users):
    ar = _make_ar(db_session, auth, users)
    sales = auth("sales")
    p = sales.post(
        "/api/v1/ar-payments",
        json={"accounts_receivable_id": ar.id, "amount": "20.00"},
    ).json()
    wh = auth("warehouse")
    r = wh.post(f"/api/v1/ar-payments/{p['id']}/void", json={})
    assert r.status_code == 403


def test_void_can_be_followed_by_new_payment(db_session, auth, users):
    """After voiding, AR should be re-payable as if nothing happened."""
    ar = _make_ar(db_session, auth, users)
    sales = auth("sales")
    p = sales.post(
        "/api/v1/ar-payments",
        json={"accounts_receivable_id": ar.id, "amount": "105.00"},
    ).json()
    sales.post(f"/api/v1/ar-payments/{p['id']}/void", json={})

    # AR should now accept a fresh full payment without complaint.
    r = sales.post(
        "/api/v1/ar-payments",
        json={"accounts_receivable_id": ar.id, "amount": "105.00"},
    )
    assert r.status_code == 201
    db_session.expire_all()
    assert db_session.get(AccountsReceivable, ar.id).status == ReceivableStatus.paid


# ---------------------- AP void tests (mirror, lighter coverage) ----------------------

def _make_ap(db_session, auth):
    supplier = make_supplier(db_session)
    product = make_product(db_session)
    admin = auth("admin")
    po = admin.post(
        "/api/v1/purchase-orders",
        json={"supplier_id": supplier.id, "items": [
            {"product_id": product.id, "quantity": 1, "unit_cost": "100.00"}
        ]},
    ).json()
    admin.post(f"/api/v1/purchase-orders/{po['id']}/receive")
    db_session.expire_all()
    return db_session.query(AccountsPayable).one()


def test_void_ap_payment_returns_to_open(db_session, auth):
    ap = _make_ap(db_session, auth)
    admin = auth("admin")
    p = admin.post(
        "/api/v1/ap-payments",
        json={"accounts_payable_id": ap.id, "amount": "105.00"},
    ).json()
    r = admin.post(f"/api/v1/ap-payments/{p['id']}/void", json={"reason": "test"})
    assert r.status_code == 200
    db_session.expire_all()
    ap = db_session.get(AccountsPayable, ap.id)
    assert ap.paid_amount == Decimal("0")
    assert ap.status == PayableStatus.open


def test_void_ap_rbac_sales_blocked(db_session, auth):
    ap = _make_ap(db_session, auth)
    admin = auth("admin")
    p = admin.post(
        "/api/v1/ap-payments",
        json={"accounts_payable_id": ap.id, "amount": "20.00"},
    ).json()
    r = auth("sales").post(f"/api/v1/ap-payments/{p['id']}/void", json={})
    assert r.status_code == 403


def test_void_ap_idempotent_guard(db_session, auth):
    ap = _make_ap(db_session, auth)
    admin = auth("admin")
    p = admin.post(
        "/api/v1/ap-payments",
        json={"accounts_payable_id": ap.id, "amount": "10.00"},
    ).json()
    admin.post(f"/api/v1/ap-payments/{p['id']}/void", json={})
    r = admin.post(f"/api/v1/ap-payments/{p['id']}/void", json={})
    assert r.status_code == 409
