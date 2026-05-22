"""Finalize step (Step 6): rewrite serial-number prefixes from backdated dates.

The backend's serial generators (``generate_so_number`` etc.) prefix the
*runtime* date — not the ``ordered_at`` / ``confirmed_at`` / ``issued_at``
the row really belongs to — because they take no historical date argument.
Result: every PO / SO / AR / AP / stock-adjustment created during a seed
run carries today's date in its number, which spoils the demo. (AR / AP
payments are the exception — their generator already uses ``paid_at`` and
needs no fix-up.)

This step walks each table, sorts rows by their effective historical
date, and rewrites the ``*_number`` column to ``PREFIX-YYYYMMDD-NNNN``
where YYYYMMDD comes from the backdated column and NNNN is the per-day
sequence (1-based, chronological within a day).

Effective-date columns:
- sales_orders:        confirmed_at (NULL fallback → ordered_at)
- purchase_orders:     received_at  (NULL fallback → ordered_at)
- accounts_receivable: issued_at
- accounts_payable:    issued_at
- stock_adjustments:   adjusted_at

Runs entirely via raw SQL against the seed engine — no API calls.
"""
from __future__ import annotations

from sqlalchemy import text

from .api_client import SeedAPIClient


_BACKFILL_SPECS: list[dict[str, str]] = [
    {
        "table": "sales_orders",
        "number_col": "so_number",
        "prefix": "SO",
        "effective_sql": "COALESCE(confirmed_at, ordered_at)",
    },
    {
        "table": "purchase_orders",
        "number_col": "po_number",
        "prefix": "PO",
        "effective_sql": "COALESCE(received_at, ordered_at)",
    },
    {
        "table": "accounts_receivable",
        "number_col": "ar_number",
        "prefix": "AR",
        "effective_sql": "issued_at",
    },
    {
        "table": "accounts_payable",
        "number_col": "ap_number",
        "prefix": "AP",
        "effective_sql": "issued_at",
    },
    {
        "table": "stock_adjustments",
        "number_col": "adjustment_number",
        "prefix": "ADJ",
        "effective_sql": "adjusted_at",
    },
]


def _backfill_one(conn, spec: dict[str, str]) -> int:
    """Rewrite *_number for one table. Returns rows updated."""
    table = spec["table"]
    number_col = spec["number_col"]
    prefix = spec["prefix"]
    effective_sql = spec["effective_sql"]

    rows = conn.execute(text(
        f"SELECT id, strftime('%Y%m%d', {effective_sql}) AS date_str "
        f"FROM {table} "
        f"ORDER BY {effective_sql}, id"
    )).fetchall()

    daily_counter: dict[str, int] = {}
    updated = 0
    for row in rows:
        date_str = row.date_str
        if date_str is None:
            # No date at all (unexpected); leave existing number alone.
            continue
        seq = daily_counter.get(date_str, 0) + 1
        daily_counter[date_str] = seq
        new_number = f"{prefix}-{date_str}-{seq:04d}"
        conn.execute(
            text(f"UPDATE {table} SET {number_col} = :n WHERE id = :id"),
            {"n": new_number, "id": row.id},
        )
        updated += 1
    return updated


def run_finalize(client: SeedAPIClient) -> None:
    """Rebuild serial-number prefixes from backdated dates."""
    print("[finalize] rewriting *_number prefixes from backdated dates ...")
    with client.engine.begin() as conn:
        for spec in _BACKFILL_SPECS:
            n = _backfill_one(conn, spec)
            print(f"[finalize]   {spec['table']}.{spec['number_col']}: {n} rows")
