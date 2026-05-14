"""rename sales/purchases to sales_orders/purchase_orders, add salesperson_id

Revision ID: b3c4d5e6f701
Revises: 7af62035ac02
Create Date: 2026-05-14 12:00:00.000000

Renames Sale-family tables/columns/indexes to SalesOrder-family,
Purchase-family to PurchaseOrder-family. Adds salesperson_id to
sales_orders (backfilled from created_by_id, then made NOT NULL).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b3c4d5e6f701"
down_revision: Union[str, None] = "7af62035ac02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- 1. Rename parent tables.
    # SQLite ≥ 3.26 updates FK references in child tables automatically.
    op.rename_table("purchases", "purchase_orders")
    op.rename_table("sales", "sales_orders")

    # ---- 2. Rename child tables.
    op.rename_table("purchase_items", "purchase_order_items")
    op.rename_table("sale_items", "sales_order_items")

    # ---- 3. Rename FK columns inside the child tables.
    with op.batch_alter_table("purchase_order_items") as batch_op:
        batch_op.alter_column(
            "purchase_id",
            new_column_name="purchase_order_id",
            existing_type=sa.Integer(),
            existing_nullable=False,
        )

    with op.batch_alter_table("sales_order_items") as batch_op:
        batch_op.alter_column(
            "sale_id",
            new_column_name="sales_order_id",
            existing_type=sa.Integer(),
            existing_nullable=False,
        )

    # ---- 4. Recreate indexes with the new naming convention.
    # purchase_orders
    with op.batch_alter_table("purchase_orders") as batch_op:
        batch_op.drop_index("ix_purchases_po_number")
        batch_op.drop_index("ix_purchases_supplier_id")
        batch_op.drop_index("ix_purchases_status")
        batch_op.drop_index("ix_purchases_created_by_id")
        batch_op.create_index("ix_purchase_orders_po_number", ["po_number"], unique=True)
        batch_op.create_index("ix_purchase_orders_supplier_id", ["supplier_id"], unique=False)
        batch_op.create_index("ix_purchase_orders_status", ["status"], unique=False)
        batch_op.create_index("ix_purchase_orders_created_by_id", ["created_by_id"], unique=False)

    # purchase_order_items
    with op.batch_alter_table("purchase_order_items") as batch_op:
        batch_op.drop_index("ix_purchase_items_purchase_id")
        batch_op.drop_index("ix_purchase_items_product_id")
        batch_op.create_index(
            "ix_purchase_order_items_purchase_order_id",
            ["purchase_order_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_purchase_order_items_product_id",
            ["product_id"],
            unique=False,
        )

    # sales_order_items
    with op.batch_alter_table("sales_order_items") as batch_op:
        batch_op.drop_index("ix_sale_items_sale_id")
        batch_op.drop_index("ix_sale_items_product_id")
        batch_op.create_index(
            "ix_sales_order_items_sales_order_id",
            ["sales_order_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_sales_order_items_product_id",
            ["product_id"],
            unique=False,
        )

    # ---- 5. sales_orders: rename indexes + add salesperson_id (nullable first).
    with op.batch_alter_table("sales_orders") as batch_op:
        batch_op.drop_index("ix_sales_so_number")
        batch_op.drop_index("ix_sales_customer_id")
        batch_op.drop_index("ix_sales_status")
        batch_op.drop_index("ix_sales_created_by_id")
        batch_op.create_index("ix_sales_orders_so_number", ["so_number"], unique=True)
        batch_op.create_index("ix_sales_orders_customer_id", ["customer_id"], unique=False)
        batch_op.create_index("ix_sales_orders_status", ["status"], unique=False)
        batch_op.create_index("ix_sales_orders_created_by_id", ["created_by_id"], unique=False)
        batch_op.add_column(sa.Column("salesperson_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_sales_orders_salesperson_id_users",
            "users",
            ["salesperson_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    # ---- 6. Backfill salesperson_id from created_by_id for existing rows.
    op.execute(
        "UPDATE sales_orders SET salesperson_id = created_by_id "
        "WHERE salesperson_id IS NULL"
    )

    # ---- 7. Flip salesperson_id to NOT NULL + index it.
    with op.batch_alter_table("sales_orders") as batch_op:
        batch_op.alter_column(
            "salesperson_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.create_index(
            "ix_sales_orders_salesperson_id",
            ["salesperson_id"],
            unique=False,
        )


def downgrade() -> None:
    # ---- Reverse Step 7: drop the new salesperson_id index, allow NULL again.
    with op.batch_alter_table("sales_orders") as batch_op:
        batch_op.drop_index("ix_sales_orders_salesperson_id")
        batch_op.alter_column(
            "salesperson_id",
            existing_type=sa.Integer(),
            nullable=True,
        )

    # ---- Reverse Steps 5–6: drop FK + salesperson_id, restore old indexes.
    with op.batch_alter_table("sales_orders") as batch_op:
        batch_op.drop_constraint("fk_sales_orders_salesperson_id_users", type_="foreignkey")
        batch_op.drop_column("salesperson_id")
        batch_op.drop_index("ix_sales_orders_so_number")
        batch_op.drop_index("ix_sales_orders_customer_id")
        batch_op.drop_index("ix_sales_orders_status")
        batch_op.drop_index("ix_sales_orders_created_by_id")
        batch_op.create_index("ix_sales_so_number", ["so_number"], unique=True)
        batch_op.create_index("ix_sales_customer_id", ["customer_id"], unique=False)
        batch_op.create_index("ix_sales_status", ["status"], unique=False)
        batch_op.create_index("ix_sales_created_by_id", ["created_by_id"], unique=False)

    # ---- Reverse Step 4: rename indexes back on the other three tables.
    with op.batch_alter_table("sales_order_items") as batch_op:
        batch_op.drop_index("ix_sales_order_items_sales_order_id")
        batch_op.drop_index("ix_sales_order_items_product_id")
        batch_op.create_index("ix_sale_items_sale_id", ["sales_order_id"], unique=False)
        batch_op.create_index("ix_sale_items_product_id", ["product_id"], unique=False)

    with op.batch_alter_table("purchase_order_items") as batch_op:
        batch_op.drop_index("ix_purchase_order_items_purchase_order_id")
        batch_op.drop_index("ix_purchase_order_items_product_id")
        batch_op.create_index("ix_purchase_items_purchase_id", ["purchase_order_id"], unique=False)
        batch_op.create_index("ix_purchase_items_product_id", ["product_id"], unique=False)

    with op.batch_alter_table("purchase_orders") as batch_op:
        batch_op.drop_index("ix_purchase_orders_po_number")
        batch_op.drop_index("ix_purchase_orders_supplier_id")
        batch_op.drop_index("ix_purchase_orders_status")
        batch_op.drop_index("ix_purchase_orders_created_by_id")
        batch_op.create_index("ix_purchases_po_number", ["po_number"], unique=True)
        batch_op.create_index("ix_purchases_supplier_id", ["supplier_id"], unique=False)
        batch_op.create_index("ix_purchases_status", ["status"], unique=False)
        batch_op.create_index("ix_purchases_created_by_id", ["created_by_id"], unique=False)

    # ---- Reverse Step 3: rename FK columns back.
    with op.batch_alter_table("sales_order_items") as batch_op:
        batch_op.alter_column(
            "sales_order_id",
            new_column_name="sale_id",
            existing_type=sa.Integer(),
            existing_nullable=False,
        )

    with op.batch_alter_table("purchase_order_items") as batch_op:
        batch_op.alter_column(
            "purchase_order_id",
            new_column_name="purchase_id",
            existing_type=sa.Integer(),
            existing_nullable=False,
        )

    # ---- Reverse Step 2: rename child tables back.
    op.rename_table("sales_order_items", "sale_items")
    op.rename_table("purchase_order_items", "purchase_items")

    # ---- Reverse Step 1: rename parent tables back.
    op.rename_table("sales_orders", "sales")
    op.rename_table("purchase_orders", "purchases")
