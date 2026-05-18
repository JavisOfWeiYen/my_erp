from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models.accounts_payable import AccountsPayable
from app.models.accounts_receivable import AccountsReceivable

from tests.factories import make_customer, make_product, make_supplier


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


def _receive_po(client, supplier_id, product_id, unit_cost="100.00"):
    po = client.post(
        "/api/v1/purchase-orders",
        json={
            "supplier_id": supplier_id,
            "items": [{"product_id": product_id, "quantity": 1, "unit_cost": unit_cost}],
        },
    ).json()
    client.post(f"/api/v1/purchase-orders/{po['id']}/receive")
    return po


def test_dashboard_empty_ar_ap(db_session, auth):
    admin = auth("admin")
    r = admin.get("/api/v1/dashboard/summary")
    assert r.status_code == 200
    body = r.json()
    assert Decimal(body["ar_balance_total"]) == Decimal("0")
    assert Decimal(body["ar_overdue_balance"]) == Decimal("0")
    assert body["ar_overdue_count"] == 0
    assert Decimal(body["ap_balance_total"]) == Decimal("0")
    assert body["ap_overdue_count"] == 0


def test_dashboard_aggregates_ar_balance(db_session, auth, users):
    customer = make_customer(db_session)
    p = make_product(db_session, stock=100)
    sales = auth("sales")
    _confirm_so(sales, customer.id, users["sales"].id, p.id)  # 105 balance
    _confirm_so(sales, customer.id, users["sales"].id, p.id, unit_price="200.00")  # 210 balance

    admin = auth("admin")
    body = admin.get("/api/v1/dashboard/summary").json()
    assert Decimal(body["ar_balance_total"]) == Decimal("315.00")
    assert body["ar_overdue_count"] == 0  # default due_date is +30 days


def test_dashboard_counts_overdue_ar(db_session, auth, users):
    customer = make_customer(db_session)
    p = make_product(db_session, stock=100)
    sales = auth("sales")
    so1 = _confirm_so(sales, customer.id, users["sales"].id, p.id)
    so2 = _confirm_so(sales, customer.id, users["sales"].id, p.id, unit_price="50.00")
    # Backdate so1 to overdue, leave so2 future.
    db_session.expire_all()
    ar1 = db_session.query(AccountsReceivable).filter_by(sales_order_id=so1["id"]).one()
    ar1.due_date = date.today() - timedelta(days=5)
    db_session.commit()

    body = sales.get("/api/v1/dashboard/summary").json()
    assert Decimal(body["ar_balance_total"]) == Decimal("105.00") + Decimal("52.50")
    assert Decimal(body["ar_overdue_balance"]) == Decimal("105.00")
    assert body["ar_overdue_count"] == 1


def test_dashboard_excludes_paid_ar(db_session, auth, users):
    customer = make_customer(db_session)
    p = make_product(db_session, stock=100)
    sales = auth("sales")
    so = _confirm_so(sales, customer.id, users["sales"].id, p.id)  # 105
    ar = db_session.query(AccountsReceivable).filter_by(sales_order_id=so["id"]).one()
    sales.post("/api/v1/ar-payments", json={"accounts_receivable_id": ar.id, "amount": "105.00"})

    body = sales.get("/api/v1/dashboard/summary").json()
    assert Decimal(body["ar_balance_total"]) == Decimal("0")


def test_dashboard_partial_ar_uses_balance(db_session, auth, users):
    customer = make_customer(db_session)
    p = make_product(db_session, stock=100)
    sales = auth("sales")
    so = _confirm_so(sales, customer.id, users["sales"].id, p.id)  # 105
    ar = db_session.query(AccountsReceivable).filter_by(sales_order_id=so["id"]).one()
    sales.post("/api/v1/ar-payments", json={"accounts_receivable_id": ar.id, "amount": "40.00"})

    body = sales.get("/api/v1/dashboard/summary").json()
    assert Decimal(body["ar_balance_total"]) == Decimal("65.00")  # 105 - 40 paid


def test_dashboard_aggregates_ap_balance_and_overdue(db_session, auth):
    supplier = make_supplier(db_session)
    p = make_product(db_session)
    admin = auth("admin")
    po = _receive_po(admin, supplier.id, p.id)
    # backdate
    db_session.expire_all()
    ap = db_session.query(AccountsPayable).filter_by(purchase_order_id=po["id"]).one()
    ap.due_date = date.today() - timedelta(days=20)
    db_session.commit()

    body = admin.get("/api/v1/dashboard/summary").json()
    assert Decimal(body["ap_balance_total"]) == Decimal("105.00")
    assert Decimal(body["ap_overdue_balance"]) == Decimal("105.00")
    assert body["ap_overdue_count"] == 1
