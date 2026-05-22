"""Reset helper (Step 6): wipe dynamic data so a clean re-run can start.

Static rows (suppliers / categories / products / customers / users / employees /
roles / menu_items) are preserved — those are idempotently re-adopted by
Steps 1-3 anyway. Transactional rows (PO / SO / AR / AP / payments /
adjustments) plus the per-product cached stock/cost are wiped back to
baseline.

Invoked by seed.py when --reset is passed. The DB session uses the
SeedAPIClient's engine so it shares the same connection settings.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text

from seed.config import products as products_cfg

from .api_client import SeedAPIClient


# Order matters: child tables first so FK constraints don't fire.
_WIPE_TABLES: tuple[str, ...] = (
    "ar_payments",
    "ap_payments",
    "accounts_receivable",
    "accounts_payable",
    "sales_order_items",
    "purchase_order_items",
    "sales_orders",
    "purchase_orders",
    "stock_adjustments",
)


def run_reset(client: SeedAPIClient) -> None:
    """DELETE all transactional rows and reset cached product state."""
    print("[reset] wiping transactional data ...")
    with client.engine.begin() as conn:
        for tbl in _WIPE_TABLES:
            # Skip tables that don't exist in this DB (older migrations).
            present = conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=:t"
                ),
                {"t": tbl},
            ).fetchone()
            if not present:
                continue
            n = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar() or 0
            conn.execute(text(f"DELETE FROM {tbl}"))
            print(f"[reset]   cleared {tbl}: {n} rows")

        # Reset stock + cost_price so subsequent timeline runs see baseline.
        conn.execute(text("UPDATE products SET stock_quantity = 0"))
        for p in products_cfg.PRODUCTS:
            conn.execute(
                text("UPDATE products SET cost_price = :c WHERE sku = :sku"),
                {"c": str(p["cost_price"]), "sku": p["sku"]},
            )
    print(
        f"[reset]   reset stock=0 + cost_price=baseline on "
        f"{len(products_cfg.PRODUCTS)} products"
    )
