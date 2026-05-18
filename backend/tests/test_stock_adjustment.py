from decimal import Decimal

import pytest

from app.models.product import Product
from app.models.stock_adjustment import StockAdjustment

from tests.factories import make_product


def _create(client, **payload):
    return client.post("/api/v1/stock-adjustments", json=payload)


def test_positive_adjustment_increases_stock(db_session, auth):
    product = make_product(db_session, stock=10)
    wh = auth("warehouse")

    r = _create(wh, product_id=product.id, change_qty=5, reason="surplus", notes="盤盈")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["before_qty"] == 10
    assert body["change_qty"] == 5
    assert body["after_qty"] == 15
    assert body["reason"] == "surplus"
    assert body["adjustment_number"].startswith("ADJ-")

    db_session.expire_all()
    p = db_session.get(Product, product.id)
    assert p.stock_quantity == 15


def test_negative_adjustment_decreases_stock(db_session, auth):
    product = make_product(db_session, stock=10)
    wh = auth("warehouse")

    r = _create(wh, product_id=product.id, change_qty=-3, reason="shortage")
    assert r.status_code == 201
    assert r.json()["after_qty"] == 7

    db_session.expire_all()
    assert db_session.get(Product, product.id).stock_quantity == 7


def test_change_qty_zero_rejected(db_session, auth):
    product = make_product(db_session, stock=5)
    wh = auth("warehouse")

    r = _create(wh, product_id=product.id, change_qty=0, reason="other")
    assert r.status_code == 400
    assert "zero" in r.json()["detail"].lower()

    db_session.expire_all()
    assert db_session.get(Product, product.id).stock_quantity == 5


def test_would_go_negative_rejected_with_math_in_message(db_session, auth):
    product = make_product(db_session, stock=2)
    wh = auth("warehouse")

    r = _create(wh, product_id=product.id, change_qty=-10, reason="scrap")
    assert r.status_code == 400
    detail = r.json()["detail"]
    # Message must show the calculation so the operator can see why.
    assert "2" in detail and "-10" in detail and "-8" in detail
    assert "negative" in detail.lower()

    db_session.expire_all()
    assert db_session.get(Product, product.id).stock_quantity == 2

    # And no adjustment row was written.
    rows = db_session.query(StockAdjustment).all()
    assert rows == []


def test_inactive_product_rejected(db_session, auth):
    product = make_product(db_session, stock=10, is_active=False)
    wh = auth("warehouse")

    r = _create(wh, product_id=product.id, change_qty=1, reason="other")
    assert r.status_code == 400
    assert "inactive" in r.json()["detail"].lower()


def test_nonexistent_product_rejected(db_session, auth):
    wh = auth("warehouse")
    r = _create(wh, product_id=99999, change_qty=1, reason="other")
    assert r.status_code == 400
    assert "does not exist" in r.json()["detail"].lower()


def test_adjustment_rbac(db_session, auth):
    product = make_product(db_session, stock=10)

    # sales cannot create adjustments
    sales = auth("sales")
    r = _create(sales, product_id=product.id, change_qty=1, reason="other")
    assert r.status_code == 403

    # warehouse can
    wh = auth("warehouse")
    r = _create(wh, product_id=product.id, change_qty=1, reason="other")
    assert r.status_code == 201


def test_adjustment_number_unique_within_same_day(db_session, auth):
    product = make_product(db_session, stock=100)
    wh = auth("warehouse")

    r1 = _create(wh, product_id=product.id, change_qty=1, reason="other")
    r2 = _create(wh, product_id=product.id, change_qty=1, reason="other")
    assert r1.status_code == 201 and r2.status_code == 201

    n1 = r1.json()["adjustment_number"]
    n2 = r2.json()["adjustment_number"]
    assert n1 != n2
    # Both share the same date prefix.
    assert n1[:13] == n2[:13]  # "ADJ-YYYYMMDD-"
