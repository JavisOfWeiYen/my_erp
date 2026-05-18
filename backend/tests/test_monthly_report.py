"""Tests for /api/v1/inventory/monthly-report.

The report rolls *current* stock backward by netting out movements after month-end,
so the same month-row should be stable when queried before, during, or after that
month. These tests pin that contract."""
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.models.purchase_order import (
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
)
from app.models.sales_order import (
    SalesOrder,
    SalesOrderItem,
    SalesOrderStatus,
)
from app.models.stock_adjustment import StockAdjustment, StockAdjustmentReason

from tests.factories import make_customer, make_product, make_supplier

REF_YEAR = 2025
REF_MONTH = 6  # target month for the "identity" property tests
TARGET_DATE = datetime(REF_YEAR, REF_MONTH, 15, 12, 0, tzinfo=timezone.utc)
BEFORE_DATE = datetime(2025, 5, 15, 12, 0, tzinfo=timezone.utc)
AFTER_DATE = datetime(2025, 7, 15, 12, 0, tzinfo=timezone.utc)


class _Seq:
    """Simple counter for unique order numbers across a single test."""

    def __init__(self, prefix: str):
        self.prefix = prefix
        self.n = 0

    def next(self) -> str:
        self.n += 1
        return f"{self.prefix}-{self.n:04d}"


def _book_received_po(db, *, supplier, product, qty, unit_cost, received_at, created_by_id, seq):
    cost = Decimal(unit_cost)
    subtotal = (cost * qty).quantize(Decimal("0.01"))
    po = PurchaseOrder(
        po_number=seq.next(),
        supplier_id=supplier.id,
        status=PurchaseOrderStatus.received,
        total_amount=subtotal,
        ordered_at=received_at,
        received_at=received_at,
        created_by_id=created_by_id,
    )
    po.items = [
        PurchaseOrderItem(
            product_id=product.id, quantity=qty, unit_cost=cost, subtotal=subtotal
        )
    ]
    db.add(po)
    product.stock_quantity = (product.stock_quantity or 0) + qty
    db.commit()
    return po


def _book_draft_or_cancelled_po(db, *, supplier, product, qty, status_, created_by_id, seq):
    cost = Decimal("10.00")
    subtotal = (cost * qty).quantize(Decimal("0.01"))
    po = PurchaseOrder(
        po_number=seq.next(),
        supplier_id=supplier.id,
        status=status_,
        total_amount=subtotal,
        ordered_at=TARGET_DATE,
        received_at=None,
        created_by_id=created_by_id,
    )
    po.items = [
        PurchaseOrderItem(
            product_id=product.id, quantity=qty, unit_cost=cost, subtotal=subtotal
        )
    ]
    db.add(po)
    db.commit()
    return po


def _book_confirmed_so(
    db, *, customer, product, qty, unit_price, confirmed_at, created_by_id, salesperson_id, seq
):
    price = Decimal(unit_price)
    subtotal = (price * qty).quantize(Decimal("0.01"))
    so = SalesOrder(
        so_number=seq.next(),
        customer_id=customer.id,
        salesperson_id=salesperson_id,
        status=SalesOrderStatus.confirmed,
        total_amount=subtotal,
        ordered_at=confirmed_at,
        confirmed_at=confirmed_at,
        created_by_id=created_by_id,
    )
    so.items = [
        SalesOrderItem(
            product_id=product.id, quantity=qty, unit_price=price, subtotal=subtotal
        )
    ]
    db.add(so)
    product.stock_quantity = (product.stock_quantity or 0) - qty
    db.commit()
    return so


def _book_draft_or_cancelled_so(
    db, *, customer, product, qty, status_, created_by_id, salesperson_id, seq
):
    price = Decimal("20.00")
    subtotal = (price * qty).quantize(Decimal("0.01"))
    so = SalesOrder(
        so_number=seq.next(),
        customer_id=customer.id,
        salesperson_id=salesperson_id,
        status=status_,
        total_amount=subtotal,
        ordered_at=TARGET_DATE,
        confirmed_at=None,
        created_by_id=created_by_id,
    )
    so.items = [
        SalesOrderItem(
            product_id=product.id, quantity=qty, unit_price=price, subtotal=subtotal
        )
    ]
    db.add(so)
    db.commit()
    return so


def _book_adjustment(
    db, *, product, change_qty, adjusted_at, operator_id, seq, reason=StockAdjustmentReason.surplus
):
    before = product.stock_quantity or 0
    after = before + change_qty
    adj = StockAdjustment(
        adjustment_number=seq.next(),
        product_id=product.id,
        before_qty=before,
        change_qty=change_qty,
        after_qty=after,
        reason=reason,
        operator_id=operator_id,
        adjusted_at=adjusted_at,
    )
    product.stock_quantity = after
    db.add(adj)
    db.commit()
    return adj


def _fetch(auth_client, *, year=REF_YEAR, month=REF_MONTH):
    r = auth_client.get(f"/api/v1/inventory/monthly-report?year={year}&month={month}")
    assert r.status_code == 200, r.text
    return r.json()


def _row_for(report, product_id: int):
    return next(r for r in report["rows"] if r["product_id"] == product_id)


def _assert_identity(report):
    """opening + qty_in - qty_out + adjustment must equal closing for every row."""
    for r in report["rows"]:
        expected = r["opening_stock"] + r["qty_in"] - r["qty_out"] + r["adjustment"]
        assert r["closing_stock"] == expected, (
            f"identity violated for {r['sku']}: "
            f"{r['opening_stock']} + {r['qty_in']} - {r['qty_out']} + {r['adjustment']} "
            f"!= {r['closing_stock']}"
        )


def test_empty_month_closing_equals_current_stock(db_session, auth):
    p = make_product(db_session, sku="EMPTY", stock=42)
    admin = auth("admin")

    report = _fetch(admin)
    row = _row_for(report, p.id)
    assert row["qty_in"] == 0
    assert row["qty_out"] == 0
    assert row["adjustment"] == 0
    assert row["closing_stock"] == 42
    assert row["opening_stock"] == 42
    _assert_identity(report)


def test_identity_holds_with_mixed_activity(db_session, auth, users):
    supplier = make_supplier(db_session)
    customer = make_customer(db_session)
    p = make_product(db_session, sku="MIX", stock=0)

    po_seq, so_seq, adj_seq = _Seq("PO-MIX"), _Seq("SO-MIX"), _Seq("ADJ-MIX")

    # Before the target month: receive 30 (sets opening = 30 going into the month)
    _book_received_po(
        db_session,
        supplier=supplier, product=p, qty=30, unit_cost="5.00",
        received_at=BEFORE_DATE, created_by_id=users["admin"].id, seq=po_seq,
    )
    # In-month: receive 20, sell 8, surplus +3, shortage -1
    _book_received_po(
        db_session,
        supplier=supplier, product=p, qty=20, unit_cost="6.00",
        received_at=TARGET_DATE, created_by_id=users["admin"].id, seq=po_seq,
    )
    _book_confirmed_so(
        db_session,
        customer=customer, product=p, qty=8, unit_price="20.00",
        confirmed_at=TARGET_DATE, created_by_id=users["sales"].id,
        salesperson_id=users["sales"].id, seq=so_seq,
    )
    _book_adjustment(
        db_session,
        product=p, change_qty=3, adjusted_at=TARGET_DATE,
        operator_id=users["warehouse"].id, seq=adj_seq,
        reason=StockAdjustmentReason.surplus,
    )
    _book_adjustment(
        db_session,
        product=p, change_qty=-1, adjusted_at=TARGET_DATE,
        operator_id=users["warehouse"].id, seq=adj_seq,
        reason=StockAdjustmentReason.shortage,
    )
    # After the target month: extra activity that must roll back correctly
    _book_received_po(
        db_session,
        supplier=supplier, product=p, qty=7, unit_cost="6.00",
        received_at=AFTER_DATE, created_by_id=users["admin"].id, seq=po_seq,
    )
    _book_confirmed_so(
        db_session,
        customer=customer, product=p, qty=2, unit_price="20.00",
        confirmed_at=AFTER_DATE, created_by_id=users["sales"].id,
        salesperson_id=users["sales"].id, seq=so_seq,
    )
    _book_adjustment(
        db_session,
        product=p, change_qty=-5, adjusted_at=AFTER_DATE,
        operator_id=users["warehouse"].id, seq=adj_seq,
        reason=StockAdjustmentReason.scrap,
    )

    admin = auth("admin")
    report = _fetch(admin)
    row = _row_for(report, p.id)
    assert row["opening_stock"] == 30
    assert row["qty_in"] == 20
    assert row["qty_out"] == 8
    assert row["adjustment"] == 2  # +3 -1
    assert row["closing_stock"] == 30 + 20 - 8 + 2  # 44
    _assert_identity(report)


def test_past_month_immutable_after_later_activity(db_session, auth, users):
    """Querying month M before vs. after later-month activity must yield identical rows."""
    supplier = make_supplier(db_session)
    customer = make_customer(db_session)
    p = make_product(db_session, sku="IMM", stock=0)

    po_seq, so_seq, adj_seq = _Seq("PO-IMM"), _Seq("SO-IMM"), _Seq("ADJ-IMM")
    # In-month activity:
    _book_received_po(
        db_session,
        supplier=supplier, product=p, qty=15, unit_cost="4.00",
        received_at=TARGET_DATE, created_by_id=users["admin"].id, seq=po_seq,
    )
    _book_confirmed_so(
        db_session,
        customer=customer, product=p, qty=4, unit_price="9.00",
        confirmed_at=TARGET_DATE, created_by_id=users["sales"].id,
        salesperson_id=users["sales"].id, seq=so_seq,
    )

    admin = auth("admin")
    snapshot_before = _fetch(admin)

    # Add lots of after-month activity.
    _book_received_po(
        db_session,
        supplier=supplier, product=p, qty=50, unit_cost="4.00",
        received_at=AFTER_DATE, created_by_id=users["admin"].id, seq=po_seq,
    )
    _book_confirmed_so(
        db_session,
        customer=customer, product=p, qty=20, unit_price="9.00",
        confirmed_at=AFTER_DATE, created_by_id=users["sales"].id,
        salesperson_id=users["sales"].id, seq=so_seq,
    )
    _book_adjustment(
        db_session,
        product=p, change_qty=-3, adjusted_at=AFTER_DATE,
        operator_id=users["warehouse"].id, seq=adj_seq,
        reason=StockAdjustmentReason.scrap,
    )

    snapshot_after = _fetch(admin)
    assert _row_for(snapshot_before, p.id) == _row_for(snapshot_after, p.id)
    assert snapshot_before["total_purchase_amount"] == snapshot_after["total_purchase_amount"]
    assert snapshot_before["total_sales_amount"] == snapshot_after["total_sales_amount"]


def test_only_received_and_confirmed_count(db_session, auth, users):
    supplier = make_supplier(db_session)
    customer = make_customer(db_session)
    p = make_product(db_session, sku="GUARD", stock=0)

    po_seq, so_seq = _Seq("PO-GUARD"), _Seq("SO-GUARD")
    # Draft / cancelled POs in the target month — must NOT contribute.
    _book_draft_or_cancelled_po(
        db_session,
        supplier=supplier, product=p, qty=99,
        status_=PurchaseOrderStatus.draft,
        created_by_id=users["admin"].id, seq=po_seq,
    )
    _book_draft_or_cancelled_po(
        db_session,
        supplier=supplier, product=p, qty=77,
        status_=PurchaseOrderStatus.cancelled,
        created_by_id=users["admin"].id, seq=po_seq,
    )
    # Draft / cancelled SOs likewise.
    _book_draft_or_cancelled_so(
        db_session,
        customer=customer, product=p, qty=11,
        status_=SalesOrderStatus.draft,
        created_by_id=users["sales"].id, salesperson_id=users["sales"].id, seq=so_seq,
    )
    _book_draft_or_cancelled_so(
        db_session,
        customer=customer, product=p, qty=22,
        status_=SalesOrderStatus.cancelled,
        created_by_id=users["sales"].id, salesperson_id=users["sales"].id, seq=so_seq,
    )

    admin = auth("admin")
    row = _row_for(_fetch(admin), p.id)
    assert row["qty_in"] == 0
    assert row["qty_out"] == 0
    assert Decimal(row["purchase_amount"]) == Decimal("0.00")
    assert Decimal(row["sales_amount"]) == Decimal("0.00")


def test_totals_match_sum_of_rows(db_session, auth, users):
    supplier = make_supplier(db_session)
    customer = make_customer(db_session)
    a = make_product(db_session, sku="A", name="A", stock=0)
    b = make_product(db_session, sku="B", name="B", stock=0)

    po_seq, so_seq = _Seq("PO-T"), _Seq("SO-T")
    _book_received_po(
        db_session,
        supplier=supplier, product=a, qty=10, unit_cost="3.00",
        received_at=TARGET_DATE, created_by_id=users["admin"].id, seq=po_seq,
    )
    _book_received_po(
        db_session,
        supplier=supplier, product=b, qty=5, unit_cost="7.00",
        received_at=TARGET_DATE, created_by_id=users["admin"].id, seq=po_seq,
    )
    _book_confirmed_so(
        db_session,
        customer=customer, product=a, qty=4, unit_price="9.00",
        confirmed_at=TARGET_DATE, created_by_id=users["sales"].id,
        salesperson_id=users["sales"].id, seq=so_seq,
    )

    admin = auth("admin")
    report = _fetch(admin)
    total_p = sum(Decimal(r["purchase_amount"]) for r in report["rows"])
    total_s = sum(Decimal(r["sales_amount"]) for r in report["rows"])
    assert Decimal(report["total_purchase_amount"]) == total_p
    assert Decimal(report["total_sales_amount"]) == total_s
    # And the explicit numbers we expect.
    assert total_p == Decimal("30.00") + Decimal("35.00")
    assert total_s == Decimal("36.00")


@pytest.mark.parametrize("year,month", [(2025, 0), (2025, 13)])
def test_invalid_month_rejected(client, auth, year, month):
    admin = auth("admin")
    r = admin.get(f"/api/v1/inventory/monthly-report?year={year}&month={month}")
    assert r.status_code == 400


def test_report_requires_auth(client):
    r = client.get(f"/api/v1/inventory/monthly-report?year={REF_YEAR}&month={REF_MONTH}")
    assert r.status_code == 401
