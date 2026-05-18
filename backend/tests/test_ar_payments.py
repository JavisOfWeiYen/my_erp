from decimal import Decimal

import pytest

from app.models.accounts_receivable import AccountsReceivable, ReceivableStatus
from app.models.ar_payment import ARPayment

from tests.factories import make_customer, make_product


def _create_and_confirm_so(client, *, customer_id, salesperson_id, items, is_tax_inclusive=False):
    payload = {
        "customer_id": customer_id,
        "salesperson_id": salesperson_id,
        "is_tax_inclusive": is_tax_inclusive,
        "items": items,
    }
    r = client.post("/api/v1/sales-orders", json=payload)
    assert r.status_code == 201, r.text
    so = r.json()
    r2 = client.post(f"/api/v1/sales-orders/{so['id']}/confirm")
    assert r2.status_code == 200, r2.text
    return so


def _make_ar(db_session, auth, users, *, total=Decimal("100.00"), inclusive=False):
    customer = make_customer(db_session)
    product = make_product(db_session, stock=100)
    sales = auth("sales")
    _create_and_confirm_so(
        sales,
        customer_id=customer.id,
        salesperson_id=users["sales"].id,
        is_tax_inclusive=inclusive,
        items=[{"product_id": product.id, "quantity": 1, "unit_price": str(total)}],
    )
    db_session.expire_all()
    return db_session.query(AccountsReceivable).one()


def test_full_payment_marks_paid(db_session, auth, users):
    ar = _make_ar(db_session, auth, users, total=Decimal("100.00"))  # → amount_total 105

    sales = auth("sales")
    r = sales.post(
        "/api/v1/ar-payments",
        json={"accounts_receivable_id": ar.id, "amount": "105.00", "method": "bank_transfer"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert Decimal(body["amount"]) == Decimal("105.00")
    assert body["payment_number"].startswith("REC-")
    assert body["method"] == "bank_transfer"

    db_session.expire_all()
    ar = db_session.get(AccountsReceivable, ar.id)
    assert ar.paid_amount == Decimal("105.00")
    assert ar.status == ReceivableStatus.paid


def test_partial_payment_marks_partial(db_session, auth, users):
    ar = _make_ar(db_session, auth, users, total=Decimal("100.00"))

    sales = auth("sales")
    r = sales.post(
        "/api/v1/ar-payments",
        json={"accounts_receivable_id": ar.id, "amount": "40.00"},
    )
    assert r.status_code == 201

    db_session.expire_all()
    ar = db_session.get(AccountsReceivable, ar.id)
    assert ar.paid_amount == Decimal("40.00")
    assert ar.status == ReceivableStatus.partial


def test_two_payments_summing_to_total_marks_paid(db_session, auth, users):
    ar = _make_ar(db_session, auth, users, total=Decimal("100.00"))

    sales = auth("sales")
    sales.post("/api/v1/ar-payments", json={"accounts_receivable_id": ar.id, "amount": "30.00"})
    sales.post("/api/v1/ar-payments", json={"accounts_receivable_id": ar.id, "amount": "75.00"})

    db_session.expire_all()
    ar = db_session.get(AccountsReceivable, ar.id)
    assert ar.paid_amount == Decimal("105.00")
    assert ar.status == ReceivableStatus.paid
    assert db_session.query(ARPayment).filter_by(accounts_receivable_id=ar.id).count() == 2


def test_overpayment_rejected(db_session, auth, users):
    ar = _make_ar(db_session, auth, users, total=Decimal("100.00"))

    sales = auth("sales")
    r = sales.post(
        "/api/v1/ar-payments",
        json={"accounts_receivable_id": ar.id, "amount": "106.00"},
    )
    assert r.status_code == 400
    assert "exceeds" in r.json()["detail"].lower()

    db_session.expire_all()
    ar = db_session.get(AccountsReceivable, ar.id)
    assert ar.paid_amount == Decimal("0")
    assert ar.status == ReceivableStatus.open
    assert db_session.query(ARPayment).count() == 0


def test_zero_or_negative_amount_rejected(db_session, auth, users):
    ar = _make_ar(db_session, auth, users)

    sales = auth("sales")
    r = sales.post(
        "/api/v1/ar-payments",
        json={"accounts_receivable_id": ar.id, "amount": "0"},
    )
    assert r.status_code == 422  # Pydantic Field(gt=0) catches it

    r2 = sales.post(
        "/api/v1/ar-payments",
        json={"accounts_receivable_id": ar.id, "amount": "-5.00"},
    )
    assert r2.status_code == 422


def test_payment_on_paid_ar_rejected(db_session, auth, users):
    ar = _make_ar(db_session, auth, users, total=Decimal("100.00"))

    sales = auth("sales")
    sales.post("/api/v1/ar-payments", json={"accounts_receivable_id": ar.id, "amount": "105.00"})
    r = sales.post("/api/v1/ar-payments", json={"accounts_receivable_id": ar.id, "amount": "1.00"})
    assert r.status_code == 409
    assert "paid" in r.json()["detail"].lower()


def test_payment_on_missing_ar_rejected(db_session, auth, users):
    sales = auth("sales")
    r = sales.post(
        "/api/v1/ar-payments",
        json={"accounts_receivable_id": 99999, "amount": "10.00"},
    )
    assert r.status_code == 400
    assert "does not exist" in r.json()["detail"].lower()


def test_rbac_warehouse_cannot_record_ar_payment(db_session, auth, users):
    ar = _make_ar(db_session, auth, users)
    wh = auth("warehouse")
    r = wh.post(
        "/api/v1/ar-payments",
        json={"accounts_receivable_id": ar.id, "amount": "10.00"},
    )
    assert r.status_code == 403


def test_list_payments_for_ar(db_session, auth, users):
    ar = _make_ar(db_session, auth, users)
    sales = auth("sales")
    sales.post("/api/v1/ar-payments", json={"accounts_receivable_id": ar.id, "amount": "20.00"})
    sales.post("/api/v1/ar-payments", json={"accounts_receivable_id": ar.id, "amount": "30.00"})

    rs = sales.get(f"/api/v1/ar-payments?accounts_receivable_id={ar.id}")
    assert rs.status_code == 200
    payments = rs.json()
    assert len(payments) == 2
    assert {Decimal(p["amount"]) for p in payments} == {Decimal("20.00"), Decimal("30.00")}


def test_ar_balance_updates_after_payment(db_session, auth, users):
    ar = _make_ar(db_session, auth, users, total=Decimal("100.00"))
    sales = auth("sales")
    sales.post("/api/v1/ar-payments", json={"accounts_receivable_id": ar.id, "amount": "40.00"})

    # Re-fetch via endpoint to see balance computed field.
    detail = sales.get(f"/api/v1/accounts-receivable/{ar.id}").json()
    assert Decimal(detail["paid_amount"]) == Decimal("40.00")
    assert Decimal(detail["balance"]) == Decimal("65.00")
    assert detail["status"] == "partial"
