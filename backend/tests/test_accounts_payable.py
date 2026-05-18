from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models.accounts_payable import AccountsPayable, PayableStatus

from tests.factories import make_product, make_supplier


def _create_po(client, *, supplier_id, items, is_tax_inclusive=False):
    payload = {
        "supplier_id": supplier_id,
        "is_tax_inclusive": is_tax_inclusive,
        "items": items,
    }
    r = client.post("/api/v1/purchase-orders", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def test_ap_created_when_po_received_exclusive(db_session, auth):
    supplier = make_supplier(db_session)
    product = make_product(db_session)

    admin = auth("admin")
    po = _create_po(
        admin,
        supplier_id=supplier.id,
        is_tax_inclusive=False,
        items=[{"product_id": product.id, "quantity": 10, "unit_cost": "100.00"}],
    )
    admin.post(f"/api/v1/purchase-orders/{po['id']}/receive")

    db_session.expire_all()
    ap = db_session.query(AccountsPayable).filter_by(purchase_order_id=po["id"]).one()
    assert ap.amount_untaxed == Decimal("1000.00")
    assert ap.tax_amount == Decimal("50.00")
    assert ap.amount_total == Decimal("1050.00")
    assert ap.paid_amount == Decimal("0")
    assert ap.status == PayableStatus.open
    assert ap.supplier_id == supplier.id
    assert ap.ap_number.startswith("AP-")
    assert ap.due_date == ap.issued_at.date() + timedelta(days=30)


def test_ap_created_when_po_received_inclusive(db_session, auth):
    supplier = make_supplier(db_session)
    product = make_product(db_session)

    admin = auth("admin")
    po = _create_po(
        admin,
        supplier_id=supplier.id,
        is_tax_inclusive=True,
        items=[{"product_id": product.id, "quantity": 1, "unit_cost": "1050.00"}],
    )
    admin.post(f"/api/v1/purchase-orders/{po['id']}/receive")

    db_session.expire_all()
    ap = db_session.query(AccountsPayable).filter_by(purchase_order_id=po["id"]).one()
    assert ap.amount_total == Decimal("1050.00")
    assert ap.amount_untaxed == Decimal("1000.00")
    assert ap.tax_amount == Decimal("50.00")


def test_ap_due_date_respects_supplier_terms(db_session, auth):
    supplier = make_supplier(db_session)
    supplier.payment_terms_days = 45
    db_session.commit()
    product = make_product(db_session)

    admin = auth("admin")
    po = _create_po(
        admin,
        supplier_id=supplier.id,
        items=[{"product_id": product.id, "quantity": 1, "unit_cost": "10.00"}],
    )
    admin.post(f"/api/v1/purchase-orders/{po['id']}/receive")

    db_session.expire_all()
    ap = db_session.query(AccountsPayable).filter_by(purchase_order_id=po["id"]).one()
    assert ap.due_date == ap.issued_at.date() + timedelta(days=45)


def test_no_ap_when_po_still_draft(db_session, auth):
    supplier = make_supplier(db_session)
    product = make_product(db_session)

    admin = auth("admin")
    _create_po(
        admin,
        supplier_id=supplier.id,
        items=[{"product_id": product.id, "quantity": 1, "unit_cost": "10.00"}],
    )

    db_session.expire_all()
    assert db_session.query(AccountsPayable).count() == 0


def test_ap_endpoint_list_and_detail(db_session, auth):
    supplier = make_supplier(db_session)
    product = make_product(db_session)

    admin = auth("admin")
    po = _create_po(
        admin,
        supplier_id=supplier.id,
        items=[{"product_id": product.id, "quantity": 5, "unit_cost": "100.00"}],
    )
    admin.post(f"/api/v1/purchase-orders/{po['id']}/receive")

    rs = admin.get("/api/v1/accounts-payable")
    assert rs.status_code == 200
    rows = rs.json()
    assert len(rows) == 1
    row = rows[0]
    assert row["purchase_order_id"] == po["id"]
    assert Decimal(row["amount_total"]) == Decimal("525.00")
    assert Decimal(row["balance"]) == Decimal("525.00")

    detail = admin.get(f"/api/v1/accounts-payable/{row['id']}")
    assert detail.status_code == 200
    assert detail.json()["ap_number"] == row["ap_number"]


def test_ap_overdue_filter(db_session, auth):
    supplier = make_supplier(db_session)
    product = make_product(db_session)

    admin = auth("admin")
    po = _create_po(
        admin,
        supplier_id=supplier.id,
        items=[{"product_id": product.id, "quantity": 1, "unit_cost": "10.00"}],
    )
    admin.post(f"/api/v1/purchase-orders/{po['id']}/receive")

    db_session.expire_all()
    ap = db_session.query(AccountsPayable).filter_by(purchase_order_id=po["id"]).one()
    ap.due_date = date.today() - timedelta(days=10)
    db_session.commit()

    rs = admin.get("/api/v1/accounts-payable?overdue_only=true")
    assert len(rs.json()) == 1
    assert rs.json()[0]["is_overdue"] is True
