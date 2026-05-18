from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.accounts_receivable import AccountsReceivable, ReceivableStatus

from tests.factories import make_customer, make_product


def _create_so(client, *, customer_id, salesperson_id, items, is_tax_inclusive=False):
    payload = {
        "customer_id": customer_id,
        "salesperson_id": salesperson_id,
        "is_tax_inclusive": is_tax_inclusive,
        "items": items,
    }
    r = client.post("/api/v1/sales-orders", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def test_ar_created_when_so_confirmed_exclusive(db_session, auth, users):
    customer = make_customer(db_session)
    # Customer default payment_terms_days = 30 (from model default)
    product = make_product(db_session, stock=100, price=Decimal("100"))

    sales = auth("sales")
    so = _create_so(
        sales,
        customer_id=customer.id,
        salesperson_id=users["sales"].id,
        is_tax_inclusive=False,
        items=[{"product_id": product.id, "quantity": 10, "unit_price": "100.00"}],
    )
    sales.post(f"/api/v1/sales-orders/{so['id']}/confirm")

    db_session.expire_all()
    ar = db_session.query(AccountsReceivable).filter_by(sales_order_id=so["id"]).one()
    assert ar.amount_untaxed == Decimal("1000.00")
    assert ar.tax_amount == Decimal("50.00")
    assert ar.amount_total == Decimal("1050.00")
    assert ar.paid_amount == Decimal("0")
    assert ar.status == ReceivableStatus.open
    assert ar.customer_id == customer.id
    assert ar.ar_number.startswith("AR-")
    # due_date = issued_at.date() + 30 days
    assert ar.due_date == ar.issued_at.date() + timedelta(days=30)


def test_ar_created_when_so_confirmed_inclusive(db_session, auth, users):
    customer = make_customer(db_session)
    product = make_product(db_session, stock=100)

    sales = auth("sales")
    so = _create_so(
        sales,
        customer_id=customer.id,
        salesperson_id=users["sales"].id,
        is_tax_inclusive=True,  # 報價已含稅
        items=[{"product_id": product.id, "quantity": 1, "unit_price": "105.00"}],
    )
    sales.post(f"/api/v1/sales-orders/{so['id']}/confirm")

    db_session.expire_all()
    ar = db_session.query(AccountsReceivable).filter_by(sales_order_id=so["id"]).one()
    assert ar.amount_total == Decimal("105.00")
    assert ar.amount_untaxed == Decimal("100.00")
    assert ar.tax_amount == Decimal("5.00")


def test_ar_due_date_respects_customer_terms(db_session, auth, users):
    customer = make_customer(db_session)
    customer.payment_terms_days = 60
    db_session.commit()
    product = make_product(db_session, stock=10)

    sales = auth("sales")
    so = _create_so(
        sales,
        customer_id=customer.id,
        salesperson_id=users["sales"].id,
        items=[{"product_id": product.id, "quantity": 1, "unit_price": "10.00"}],
    )
    sales.post(f"/api/v1/sales-orders/{so['id']}/confirm")

    db_session.expire_all()
    ar = db_session.query(AccountsReceivable).filter_by(sales_order_id=so["id"]).one()
    assert ar.due_date == ar.issued_at.date() + timedelta(days=60)


def test_ar_cash_terms_due_today(db_session, auth, users):
    customer = make_customer(db_session)
    customer.payment_terms_days = 0
    db_session.commit()
    product = make_product(db_session, stock=10)

    sales = auth("sales")
    so = _create_so(
        sales,
        customer_id=customer.id,
        salesperson_id=users["sales"].id,
        items=[{"product_id": product.id, "quantity": 1, "unit_price": "10.00"}],
    )
    sales.post(f"/api/v1/sales-orders/{so['id']}/confirm")

    db_session.expire_all()
    ar = db_session.query(AccountsReceivable).filter_by(sales_order_id=so["id"]).one()
    assert ar.due_date == ar.issued_at.date()


def test_no_ar_when_so_still_draft_or_cancelled(db_session, auth, users):
    customer = make_customer(db_session)
    product = make_product(db_session, stock=10)

    sales = auth("sales")
    draft_so = _create_so(
        sales,
        customer_id=customer.id,
        salesperson_id=users["sales"].id,
        items=[{"product_id": product.id, "quantity": 1, "unit_price": "10.00"}],
    )
    cancelled_so = _create_so(
        sales,
        customer_id=customer.id,
        salesperson_id=users["sales"].id,
        items=[{"product_id": product.id, "quantity": 1, "unit_price": "10.00"}],
    )
    sales.post(f"/api/v1/sales-orders/{cancelled_so['id']}/cancel")

    db_session.expire_all()
    assert db_session.query(AccountsReceivable).count() == 0


def test_ar_endpoint_list_and_detail(db_session, auth, users):
    customer = make_customer(db_session)
    product = make_product(db_session, stock=10)

    sales = auth("sales")
    so = _create_so(
        sales,
        customer_id=customer.id,
        salesperson_id=users["sales"].id,
        items=[{"product_id": product.id, "quantity": 2, "unit_price": "50.00"}],
    )
    sales.post(f"/api/v1/sales-orders/{so['id']}/confirm")

    admin = auth("admin")
    rs = admin.get("/api/v1/accounts-receivable")
    assert rs.status_code == 200
    rows = rs.json()
    assert len(rows) == 1
    row = rows[0]
    assert row["sales_order_id"] == so["id"]
    assert Decimal(row["amount_total"]) == Decimal("105.00")
    assert Decimal(row["balance"]) == Decimal("105.00")
    assert row["is_overdue"] is False  # due_date is in the future

    detail = admin.get(f"/api/v1/accounts-receivable/{row['id']}")
    assert detail.status_code == 200
    assert detail.json()["ar_number"] == row["ar_number"]


def test_ar_filter_by_customer_and_status(db_session, auth, users):
    a = make_customer(db_session, name="A")
    b = make_customer(db_session, name="B")
    p = make_product(db_session, stock=100)

    sales = auth("sales")
    for cust in (a, b):
        so = _create_so(
            sales,
            customer_id=cust.id,
            salesperson_id=users["sales"].id,
            items=[{"product_id": p.id, "quantity": 1, "unit_price": "100.00"}],
        )
        sales.post(f"/api/v1/sales-orders/{so['id']}/confirm")

    admin = auth("admin")
    rs = admin.get(f"/api/v1/accounts-receivable?customer_id={a.id}")
    assert rs.status_code == 200
    rows = rs.json()
    assert len(rows) == 1
    assert rows[0]["customer_id"] == a.id

    rs2 = admin.get("/api/v1/accounts-receivable?status_filter=open")
    assert len(rs2.json()) == 2


def test_ar_overdue_filter(db_session, auth, users):
    """An AR with due_date in the past should appear in overdue_only."""
    customer = make_customer(db_session)
    product = make_product(db_session, stock=10)

    sales = auth("sales")
    so = _create_so(
        sales,
        customer_id=customer.id,
        salesperson_id=users["sales"].id,
        items=[{"product_id": product.id, "quantity": 1, "unit_price": "10.00"}],
    )
    sales.post(f"/api/v1/sales-orders/{so['id']}/confirm")

    # Backdate the due_date 5 days ago to simulate an overdue AR.
    db_session.expire_all()
    ar = db_session.query(AccountsReceivable).filter_by(sales_order_id=so["id"]).one()
    ar.due_date = date.today() - timedelta(days=5)
    db_session.commit()

    admin = auth("admin")
    rs = admin.get("/api/v1/accounts-receivable?overdue_only=true")
    assert rs.status_code == 200
    rows = rs.json()
    assert len(rows) == 1
    assert rows[0]["is_overdue"] is True
