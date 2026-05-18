from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models.accounts_receivable import AccountsReceivable, ReceivableStatus

from tests.factories import make_customer, make_product


def _confirm_so(client, customer, salesperson_id, product, unit_price="100.00"):
    so = client.post(
        "/api/v1/sales-orders",
        json={
            "customer_id": customer.id,
            "salesperson_id": salesperson_id,
            "items": [{"product_id": product.id, "quantity": 1, "unit_price": unit_price}],
        },
    ).json()
    client.post(f"/api/v1/sales-orders/{so['id']}/confirm")
    return so


def _set_ar_due(db_session, sales_order_id, due_date):
    ar = db_session.query(AccountsReceivable).filter_by(sales_order_id=sales_order_id).one()
    ar.due_date = due_date
    db_session.commit()
    return ar


def test_aging_buckets_classification(db_session, auth, users):
    customer = make_customer(db_session, name="C1")
    product = make_product(db_session, stock=1000)
    sales = auth("sales")
    today = date.today()

    # Create 5 ARs, each $105 (100 + 5% tax), then backdate due_dates into each bucket.
    sos = []
    for _ in range(5):
        sos.append(_confirm_so(sales, customer, users["sales"].id, product))

    _set_ar_due(db_session, sos[0]["id"], today + timedelta(days=5))    # not_due
    _set_ar_due(db_session, sos[1]["id"], today - timedelta(days=10))   # d1_30
    _set_ar_due(db_session, sos[2]["id"], today - timedelta(days=45))   # d31_60
    _set_ar_due(db_session, sos[3]["id"], today - timedelta(days=75))   # d61_90
    _set_ar_due(db_session, sos[4]["id"], today - timedelta(days=120))  # d90_plus

    r = sales.get("/api/v1/accounts-receivable/aging")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["as_of"] == today.isoformat()
    assert len(body["rows"]) == 1
    row = body["rows"][0]
    assert row["customer_name"] == "C1"
    b = row["buckets"]
    assert Decimal(b["not_due"]) == Decimal("105.00")
    assert Decimal(b["d1_30"]) == Decimal("105.00")
    assert Decimal(b["d31_60"]) == Decimal("105.00")
    assert Decimal(b["d61_90"]) == Decimal("105.00")
    assert Decimal(b["d90_plus"]) == Decimal("105.00")
    assert Decimal(b["total"]) == Decimal("525.00")

    # Totals match row sums (single customer here so identical).
    t = body["totals"]
    assert Decimal(t["total"]) == Decimal("525.00")


def test_aging_boundary_days(db_session, auth, users):
    """30-day, 60-day, 90-day boundaries land in the correct bucket."""
    customer = make_customer(db_session)
    product = make_product(db_session, stock=100)
    sales = auth("sales")
    today = date.today()

    sos = [_confirm_so(sales, customer, users["sales"].id, product) for _ in range(4)]
    _set_ar_due(db_session, sos[0]["id"], today)                   # not_due (>= today)
    _set_ar_due(db_session, sos[1]["id"], today - timedelta(days=30))  # d1_30
    _set_ar_due(db_session, sos[2]["id"], today - timedelta(days=60))  # d31_60
    _set_ar_due(db_session, sos[3]["id"], today - timedelta(days=90))  # d61_90

    r = sales.get("/api/v1/accounts-receivable/aging")
    b = r.json()["rows"][0]["buckets"]
    assert Decimal(b["not_due"]) == Decimal("105.00")   # day 0 = not_due
    assert Decimal(b["d1_30"]) == Decimal("105.00")     # day 30 inclusive
    assert Decimal(b["d31_60"]) == Decimal("105.00")    # day 60 inclusive
    assert Decimal(b["d61_90"]) == Decimal("105.00")    # day 90 inclusive
    assert Decimal(b["d90_plus"]) == Decimal("0")


def test_paid_ar_excluded_from_aging(db_session, auth, users):
    customer = make_customer(db_session)
    product = make_product(db_session, stock=100)
    sales = auth("sales")
    so = _confirm_so(sales, customer, users["sales"].id, product)
    sales.post(
        "/api/v1/ar-payments",
        json={"accounts_receivable_id":
              db_session.query(AccountsReceivable).filter_by(sales_order_id=so["id"]).one().id,
              "amount": "105.00"},
    )

    r = sales.get("/api/v1/accounts-receivable/aging")
    assert r.status_code == 200
    body = r.json()
    assert body["rows"] == []
    assert Decimal(body["totals"]["total"]) == Decimal("0")


def test_partial_ar_includes_remaining_balance(db_session, auth, users):
    customer = make_customer(db_session)
    product = make_product(db_session, stock=100)
    sales = auth("sales")
    so = _confirm_so(sales, customer, users["sales"].id, product)  # 105 total
    ar_id = db_session.query(AccountsReceivable).filter_by(sales_order_id=so["id"]).one().id
    sales.post("/api/v1/ar-payments", json={"accounts_receivable_id": ar_id, "amount": "60.00"})

    r = sales.get("/api/v1/accounts-receivable/aging")
    row = r.json()["rows"][0]
    # Remaining balance 45 lands in not_due (due_date is 30 days from confirm).
    assert Decimal(row["buckets"]["not_due"]) == Decimal("45.00")
    assert Decimal(row["buckets"]["total"]) == Decimal("45.00")


def test_aging_groups_by_customer_sorted_by_total(db_session, auth, users):
    a = make_customer(db_session, name="Acme")
    b = make_customer(db_session, name="Beta")
    product = make_product(db_session, stock=1000)
    sales = auth("sales")
    # A gets 2 ARs of 100; B gets 1 AR of 500
    _confirm_so(sales, a, users["sales"].id, product, unit_price="100.00")
    _confirm_so(sales, a, users["sales"].id, product, unit_price="100.00")
    _confirm_so(sales, b, users["sales"].id, product, unit_price="500.00")

    r = sales.get("/api/v1/accounts-receivable/aging")
    rows = r.json()["rows"]
    assert len(rows) == 2
    # B (total 525) should come before A (total 210)
    assert rows[0]["customer_name"] == "Beta"
    assert Decimal(rows[0]["buckets"]["total"]) == Decimal("525.00")
    assert rows[1]["customer_name"] == "Acme"
    assert Decimal(rows[1]["buckets"]["total"]) == Decimal("210.00")


def test_aging_as_of_parameter(db_session, auth, users):
    """Querying at a past date should reclassify rows whose due_date hadn't passed yet."""
    customer = make_customer(db_session)
    product = make_product(db_session, stock=100)
    sales = auth("sales")
    today = date.today()

    so = _confirm_so(sales, customer, users["sales"].id, product)
    # Due in 5 days from today.
    _set_ar_due(db_session, so["id"], today + timedelta(days=5))

    # As-of today: not_due
    r1 = sales.get("/api/v1/accounts-receivable/aging")
    assert Decimal(r1.json()["rows"][0]["buckets"]["not_due"]) == Decimal("105.00")

    # As-of 10 days from now (5 days past due_date): d1_30
    future = (today + timedelta(days=10)).isoformat()
    r2 = sales.get(f"/api/v1/accounts-receivable/aging?as_of={future}")
    assert Decimal(r2.json()["rows"][0]["buckets"]["d1_30"]) == Decimal("105.00")
