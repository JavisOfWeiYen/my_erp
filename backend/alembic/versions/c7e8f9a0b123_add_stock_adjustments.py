"""add stock_adjustments table

Revision ID: c7e8f9a0b123
Revises: b3c4d5e6f701
Create Date: 2026-05-14 15:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7e8f9a0b123"
down_revision: Union[str, None] = "b3c4d5e6f701"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stock_adjustments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("adjustment_number", sa.String(length=32), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("before_qty", sa.Integer(), nullable=False),
        sa.Column("change_qty", sa.Integer(), nullable=False),
        sa.Column("after_qty", sa.Integer(), nullable=False),
        sa.Column(
            "reason",
            sa.Enum(
                "surplus", "shortage", "scrap", "other",
                name="stock_adjustment_reason",
            ),
            nullable=False,
        ),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("operator_id", sa.Integer(), nullable=False),
        sa.Column(
            "adjusted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint("change_qty != 0", name="ck_stock_adjustments_change_nonzero"),
        sa.CheckConstraint("after_qty >= 0", name="ck_stock_adjustments_after_qty_non_negative"),
        sa.CheckConstraint(
            "after_qty = before_qty + change_qty",
            name="ck_stock_adjustments_qty_math",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["operator_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("stock_adjustments", schema=None) as batch_op:
        batch_op.create_index(
            "ix_stock_adjustments_adjustment_number",
            ["adjustment_number"],
            unique=True,
        )
        batch_op.create_index("ix_stock_adjustments_product_id", ["product_id"], unique=False)
        batch_op.create_index("ix_stock_adjustments_operator_id", ["operator_id"], unique=False)
        batch_op.create_index("ix_stock_adjustments_reason", ["reason"], unique=False)
        batch_op.create_index("ix_stock_adjustments_adjusted_at", ["adjusted_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("stock_adjustments", schema=None) as batch_op:
        batch_op.drop_index("ix_stock_adjustments_adjusted_at")
        batch_op.drop_index("ix_stock_adjustments_reason")
        batch_op.drop_index("ix_stock_adjustments_operator_id")
        batch_op.drop_index("ix_stock_adjustments_product_id")
        batch_op.drop_index("ix_stock_adjustments_adjustment_number")
    op.drop_table("stock_adjustments")
