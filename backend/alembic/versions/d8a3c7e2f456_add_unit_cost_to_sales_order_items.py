"""add unit_cost to sales_order_items with historical backfill

Revision ID: d8a3c7e2f456
Revises: 2094746b9c0a
Create Date: 2026-05-19 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8a3c7e2f456'
down_revision: Union[str, None] = '2094746b9c0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('sales_order_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('unit_cost', sa.Numeric(12, 2), nullable=True))
        batch_op.create_check_constraint(
            'ck_sales_order_items_unit_cost_non_negative',
            'unit_cost IS NULL OR unit_cost >= 0',
        )

    # Backfill snapshot cost on historical confirmed sales-order items.
    # Strategy:
    #   1) Most recent received PO line for the same product, on or before confirmed_at.
    #   2) Otherwise the product's current cost_price.
    #   3) Otherwise 0.
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT soi.id, soi.product_id, so.confirmed_at "
            "FROM sales_order_items soi "
            "JOIN sales_orders so ON so.id = soi.sales_order_id "
            "WHERE so.status = 'confirmed' AND soi.unit_cost IS NULL"
        )
    ).fetchall()

    for item_id, product_id, confirmed_at in rows:
        cost_row = bind.execute(
            sa.text(
                "SELECT poi.unit_cost "
                "FROM purchase_order_items poi "
                "JOIN purchase_orders po ON po.id = poi.purchase_order_id "
                "WHERE poi.product_id = :pid "
                "  AND po.status = 'received' "
                "  AND po.received_at IS NOT NULL "
                "  AND po.received_at <= :cdate "
                "ORDER BY po.received_at DESC "
                "LIMIT 1"
            ),
            {"pid": product_id, "cdate": confirmed_at},
        ).fetchone()
        if cost_row is None:
            cost_row = bind.execute(
                sa.text("SELECT cost_price FROM products WHERE id = :pid"),
                {"pid": product_id},
            ).fetchone()
        unit_cost = cost_row[0] if cost_row and cost_row[0] is not None else 0
        bind.execute(
            sa.text(
                "UPDATE sales_order_items SET unit_cost = :cost WHERE id = :id"
            ),
            {"cost": unit_cost, "id": item_id},
        )


def downgrade() -> None:
    with op.batch_alter_table('sales_order_items', schema=None) as batch_op:
        batch_op.drop_constraint(
            'ck_sales_order_items_unit_cost_non_negative', type_='check'
        )
        batch_op.drop_column('unit_cost')
