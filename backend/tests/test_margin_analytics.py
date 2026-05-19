from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.core.database import SessionLocal
from app.models.product import Product
from app.models.sales_order import SalesOrder, SalesOrderItem, SalesOrderStatus

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


def _confirm(client, order_id):
    r = client.post(f"/api/v1/sales-orders/{order_id}/confirm")
    assert r.status_code == 200, r.text
    return r.json()


def _backdate_confirmed(order_id, when: datetime):
    """Force a confirmed sales-order's confirmed_at to a specific moment.

    Tests that exercise date filtering and trend buckets need historical
    confirmations; this is the cleanest way without inventing an admin API.
    """
    s = SessionLocal()
    try:
        order = s.get(SalesOrder, order_id)
        order.confirmed_at = when
        s.commit()
    finally:
        s.close()


# ---------------------------------------------------------------------------
# confirm() snapshot behaviour
# ---------------------------------------------------------------------------

def test_confirm_snapshots_unit_cost(db_session, auth, users):
    customer = make_customer(db_session)
    product = make_product(
        db_session, stock=20, cost=Decimal("12.50"), price=Decimal("50.00")
    )

    sales = auth("sales")
    so = _create_draft(
        sales,
        customer.id,
        users["sales"].id,
        [{"product_id": product.id, "quantity": 4, "unit_price": "50.00"}],
    )
    body = _confirm(sales, so["id"])
    assert body["items"][0]["unit_cost"] == "12.50"

    db_session.expire_all()
    items = list(db_session.query(SalesOrderItem).filter_by(sales_order_id=so["id"]))
    assert len(items) == 1
    assert items[0].unit_cost == Decimal("12.50")


def test_confirm_snapshot_does_not_track_later_cost_changes(db_session, auth, users):
    customer = make_customer(db_session)
    product = make_product(
        db_session, stock=20, cost=Decimal("10.00"), price=Decimal("30.00")
    )

    sales = auth("sales")
    so = _create_draft(
        sales,
        customer.id,
        users["sales"].id,
        [{"product_id": product.id, "quantity": 2, "unit_price": "30.00"}],
    )
    _confirm(sales, so["id"])

    # Cost rises after the fact — historical line must remain frozen.
    db_session.expire_all()
    p = db_session.get(Product, product.id)
    p.cost_price = Decimal("99.00")
    db_session.commit()

    db_session.expire_all()
    item = db_session.query(SalesOrderItem).filter_by(sales_order_id=so["id"]).one()
    assert item.unit_cost == Decimal("10.00")


def test_draft_and_cancelled_have_null_unit_cost(db_session, auth, users):
    customer = make_customer(db_session)
    product = make_product(
        db_session, stock=20, cost=Decimal("5.00"), price=Decimal("20.00")
    )

    sales = auth("sales")
    so = _create_draft(
        sales,
        customer.id,
        users["sales"].id,
        [{"product_id": product.id, "quantity": 1, "unit_price": "20.00"}],
    )
    # Still draft → unit_cost must be NULL
    item = db_session.query(SalesOrderItem).filter_by(sales_order_id=so["id"]).one()
    db_session.refresh(item)
    assert item.unit_cost is None

    # Cancel → still NULL (no snapshot ever taken)
    r = sales.post(f"/api/v1/sales-orders/{so['id']}/cancel")
    assert r.status_code == 200
    db_session.expire_all()
    item = db_session.query(SalesOrderItem).filter_by(sales_order_id=so["id"]).one()
    assert item.unit_cost is None


# ---------------------------------------------------------------------------
# /analytics/margin/by-product
# ---------------------------------------------------------------------------

def test_margin_by_product_basic(db_session, auth, users):
    customer = make_customer(db_session)
    p1 = make_product(
        db_session, sku="P1", name="P1",
        stock=100, cost=Decimal("10.00"), price=Decimal("30.00"),
    )
    p2 = make_product(
        db_session, sku="P2", name="P2",
        stock=100, cost=Decimal("20.00"), price=Decimal("25.00"),
    )

    sales = auth("sales")
    so = _create_draft(
        sales,
        customer.id,
        users["sales"].id,
        [
            {"product_id": p1.id, "quantity": 5, "unit_price": "30.00"},  # rev 150, cost 50
            {"product_id": p2.id, "quantity": 4, "unit_price": "25.00"},  # rev 100, cost 80
        ],
    )
    _confirm(sales, so["id"])

    r = sales.get("/api/v1/analytics/margin/by-product")
    assert r.status_code == 200, r.text
    body = r.json()
    rows = {row["sku"]: row for row in body["rows"]}
    assert rows["P1"]["revenue"] == "150.00"
    assert rows["P1"]["cost"] == "50.00"
    assert rows["P1"]["gross_profit"] == "100.00"
    # 100/150 = 0.6667
    assert rows["P1"]["margin_rate"] == "0.6667"
    assert rows["P2"]["revenue"] == "100.00"
    assert rows["P2"]["cost"] == "80.00"
    assert rows["P2"]["margin_rate"] == "0.2000"

    # Default sort = margin_rate desc → P1 first
    assert body["rows"][0]["sku"] == "P1"

    assert body["total_revenue"] == "250.00"
    assert body["total_cost"] == "130.00"
    assert body["total_gross_profit"] == "120.00"
    assert body["overall_margin_rate"] == "0.4800"


def test_margin_by_product_excludes_draft_and_cancelled(db_session, auth, users):
    customer = make_customer(db_session)
    p = make_product(
        db_session, sku="P", name="P",
        stock=100, cost=Decimal("10.00"), price=Decimal("30.00"),
    )

    sales = auth("sales")
    # draft, never confirmed
    _create_draft(
        sales,
        customer.id,
        users["sales"].id,
        [{"product_id": p.id, "quantity": 3, "unit_price": "30.00"}],
    )
    # cancelled
    so2 = _create_draft(
        sales,
        customer.id,
        users["sales"].id,
        [{"product_id": p.id, "quantity": 2, "unit_price": "30.00"}],
    )
    sales.post(f"/api/v1/sales-orders/{so2['id']}/cancel")

    r = sales.get("/api/v1/analytics/margin/by-product")
    assert r.status_code == 200
    body = r.json()
    assert body["rows"] == []
    assert body["total_revenue"] == "0.00"


def test_margin_by_product_sort_by_revenue(db_session, auth, users):
    customer = make_customer(db_session)
    high_rev = make_product(
        db_session, sku="HIGH", name="High",
        stock=100, cost=Decimal("90.00"), price=Decimal("100.00"),  # margin 10%
    )
    high_margin = make_product(
        db_session, sku="MARG", name="Margin",
        stock=100, cost=Decimal("10.00"), price=Decimal("50.00"),  # margin 80%
    )

    sales = auth("sales")
    so = _create_draft(
        sales,
        customer.id,
        users["sales"].id,
        [
            {"product_id": high_rev.id, "quantity": 10, "unit_price": "100.00"},
            {"product_id": high_margin.id, "quantity": 1, "unit_price": "50.00"},
        ],
    )
    _confirm(sales, so["id"])

    r = sales.get(
        "/api/v1/analytics/margin/by-product", params={"sort_by": "revenue"}
    )
    body = r.json()
    assert body["rows"][0]["sku"] == "HIGH"
    assert body["rows"][1]["sku"] == "MARG"


def test_margin_by_product_date_filter(db_session, auth, users):
    customer = make_customer(db_session)
    p = make_product(
        db_session, sku="P", name="P",
        stock=100, cost=Decimal("10.00"), price=Decimal("30.00"),
    )

    sales = auth("sales")
    # 2025-03 order
    so_old = _create_draft(
        sales,
        customer.id,
        users["sales"].id,
        [{"product_id": p.id, "quantity": 2, "unit_price": "30.00"}],
    )
    _confirm(sales, so_old["id"])
    _backdate_confirmed(so_old["id"], datetime(2025, 3, 15, tzinfo=timezone.utc))

    # 2026-04 order
    so_recent = _create_draft(
        sales,
        customer.id,
        users["sales"].id,
        [{"product_id": p.id, "quantity": 5, "unit_price": "30.00"}],
    )
    _confirm(sales, so_recent["id"])
    _backdate_confirmed(so_recent["id"], datetime(2026, 4, 10, tzinfo=timezone.utc))

    r = sales.get(
        "/api/v1/analytics/margin/by-product",
        params={"start_date": "2026-01-01", "end_date": "2026-12-31"},
    )
    body = r.json()
    assert body["total_revenue"] == "150.00"  # 5 * 30
    assert len(body["rows"]) == 1


# ---------------------------------------------------------------------------
# /analytics/margin/by-customer
# ---------------------------------------------------------------------------

def test_margin_by_customer_basic(db_session, auth, users):
    high_margin_cust = make_customer(db_session, name="HighMargin")
    low_margin_cust = make_customer(db_session, name="LowMargin")
    p = make_product(
        db_session, sku="P", name="P",
        stock=1000, cost=Decimal("10.00"), price=Decimal("30.00"),
    )

    sales = auth("sales")
    # HighMargin pays full price
    hm_so = _create_draft(
        sales, high_margin_cust.id, users["sales"].id,
        [{"product_id": p.id, "quantity": 5, "unit_price": "30.00"}],
    )
    _confirm(sales, hm_so["id"])
    # LowMargin negotiated a discount — same cost, lower price
    lm_so = _create_draft(
        sales, low_margin_cust.id, users["sales"].id,
        [{"product_id": p.id, "quantity": 10, "unit_price": "12.00"}],
    )
    _confirm(sales, lm_so["id"])

    r = sales.get("/api/v1/analytics/margin/by-customer")
    assert r.status_code == 200
    body = r.json()
    by_name = {row["customer_name"]: row for row in body["rows"]}
    assert by_name["HighMargin"]["revenue"] == "150.00"
    assert by_name["HighMargin"]["margin_rate"] == "0.6667"
    assert by_name["LowMargin"]["revenue"] == "120.00"
    # 10 cost vs 12 price → margin = 2/12 = 0.1667
    assert by_name["LowMargin"]["margin_rate"] == "0.1667"
    # Default sort = margin_rate desc — HighMargin first even though revenue tied
    assert body["rows"][0]["customer_name"] == "HighMargin"


# ---------------------------------------------------------------------------
# /analytics/margin/trend
# ---------------------------------------------------------------------------

def test_margin_trend_returns_n_buckets(db_session, auth, users):
    sales = auth("sales")
    r = sales.get("/api/v1/analytics/margin/trend", params={"months": 6})
    assert r.status_code == 200
    body = r.json()
    assert body["months"] == 6
    assert len(body["rows"]) == 6
    # All zero — no orders.
    assert all(row["revenue"] == "0.00" for row in body["rows"])
    # Ordered chronologically (oldest first).
    years_months = [(row["year"], row["month"]) for row in body["rows"]]
    assert years_months == sorted(years_months)


def test_margin_trend_aggregates_into_correct_bucket(db_session, auth, users):
    customer = make_customer(db_session)
    p = make_product(
        db_session, sku="P", name="P",
        stock=1000, cost=Decimal("10.00"), price=Decimal("25.00"),
    )

    sales = auth("sales")
    so = _create_draft(
        sales, customer.id, users["sales"].id,
        [{"product_id": p.id, "quantity": 4, "unit_price": "25.00"}],
    )
    _confirm(sales, so["id"])
    # Backdate to within the current month so it lands in the latest bucket.
    now = datetime.now(timezone.utc)
    _backdate_confirmed(so["id"], now - timedelta(hours=1))

    r = sales.get("/api/v1/analytics/margin/trend", params={"months": 3})
    body = r.json()
    last = body["rows"][-1]
    assert last["year"] == now.year
    assert last["month"] == now.month
    assert last["quantity"] == 4
    assert last["revenue"] == "100.00"
    assert last["cost"] == "40.00"
    assert last["gross_profit"] == "60.00"
    assert last["margin_rate"] == "0.6000"
    assert last["avg_unit_price"] == "25.00"
    assert last["avg_unit_cost"] == "10.00"


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def test_analytics_requires_authentication(client):
    r = client.get("/api/v1/analytics/margin/by-product")
    assert r.status_code == 401
    r = client.get("/api/v1/analytics/margin/by-customer")
    assert r.status_code == 401
    r = client.get("/api/v1/analytics/margin/trend")
    assert r.status_code == 401
