"""Timeline generator (Step 4): 18-month PO/SO main loop.

Strategy is a two-pass plan:

1. **Plan** (pure computation) — walk every (customer, month) and decide what
   each customer would buy: target value, target margin, line items.
   Aggregates demand per (sku, month) into a PO requirements table.
2. **Execute** (API + SQL) — for each month:
   - Build one PO per supplier covering that month's planned demand (plus a
     small safety buffer). POST + /receive. Backdate timestamps.
   - For each planned SO, POST + /confirm. Backdate confirmed_at / created_at
     + AR.issued_at / AR.due_date. On stock shortage, halve quantity once
     and retry; on second failure, skip and log.

Two-pass keeps stock from over-buying. SOs are planned without API contact,
so we know exactly how many units to bring in.

Cost-hike events compound `product.cost_price * Π multipliers`. The PO
unit_cost passed in carries the hiked value — the backend's `/receive`
writes it back, so subsequent SO confirms in the same (or later) month
snapshot the hiked cost.

Stockouts (`STOCKOUT_EVENTS`) cut the PO received quantity for the affected
SKU in the listed months — SOs that fall through naturally fail confirm.

The whole run is deterministic via `RNG_SEED` in ``_timeline_util``.
"""
from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from seed.config import customers as customers_cfg
from seed.config import products as products_cfg
from seed.config import stories
from seed.config import suppliers as suppliers_cfg

from . import _timeline_util as tu
from .api_client import SeedAPIClient, SeedAPIError
from .seed_setup import SeedState


# ── Per-category baseline PO quantities (before quarterly multiplier) ─
# Used as a safety buffer on top of planned demand so analytics get some
# inventory drift instead of a zero-residual stock at every month end.
SAFETY_BUFFER_PCT = Decimal("0.15")


@dataclass
class PlannedItem:
    sku: str
    quantity: int
    unit_price: Decimal


@dataclass
class PlannedSO:
    customer_code: str
    salesperson_code: str
    items: list[PlannedItem]
    ordered_dt: datetime
    confirm_dt: datetime
    is_tax_inclusive: bool = False


# ── PLAN PASS ────────────────────────────────────────────────────────


def _eligible_skus(category: str, month_start: date) -> list[dict[str, Any]]:
    ym = tu.year_month_key(month_start)
    return [
        p for p in products_cfg.by_category(category)
        if p["launch_month"] <= ym
    ]


def _build_items(
    target_value: Decimal,
    margin_pct: int,
    preferred_categories: list[str],
    month_start: date,
    rng: random.Random,
) -> list[PlannedItem]:
    """Compose 1-3 line items whose total roughly matches ``target_value``."""
    items: list[PlannedItem] = []
    remaining = target_value
    max_lines = 3
    margin = Decimal(margin_pct) / Decimal(100)

    # Sample categories with repetition allowed — small orders might double
    # up the same category.
    for _ in range(max_lines):
        if remaining < Decimal("3000"):
            break
        category = rng.choice(preferred_categories)
        candidates = _eligible_skus(category, month_start)
        if not candidates:
            continue
        product = rng.choice(candidates)
        # Customer pricing is sticky: priced off baseline cost, not the
        # cost-hiked snapshot. When suppliers raise costs (COST_HIKE_EVENTS)
        # the unit_price stays put → margin compresses naturally because
        # confirm() snapshots the *current* (hiked) cost into unit_cost.
        baseline_cost = product["cost_price"]
        unit_price = (baseline_cost * (Decimal("1") + margin)).quantize(Decimal("1"))
        if unit_price <= 0:
            continue
        # Decide qty: try to use 40-90% of remaining, ≥ 1.
        target_qty = remaining / unit_price
        if target_qty < Decimal("1"):
            qty = 1
        else:
            qty = max(1, int(round(float(target_qty) * rng.uniform(0.4, 0.9))))
        items.append(PlannedItem(sku=product["sku"], quantity=qty, unit_price=unit_price))
        remaining -= qty * unit_price

    if not items:
        # Fallback: 1 unit of cheapest eligible SKU in the first preferred category.
        for cat in preferred_categories:
            cands = _eligible_skus(cat, month_start)
            if not cands:
                continue
            cheapest = min(cands, key=lambda p: p["unit_price"])
            cost = cheapest["cost_price"] * tu.cumulative_cost_multiplier(cheapest["sku"], month_start)
            unit_price = (cost * (Decimal("1") + margin)).quantize(Decimal("1"))
            items.append(PlannedItem(sku=cheapest["sku"], quantity=1, unit_price=unit_price))
            break

    return items


def _so_datetimes(month_start: date, rng: random.Random) -> tuple[datetime, datetime]:
    """Pick (ordered_dt, confirm_dt) inside the month; confirm 0-3 days later."""
    ordered = tu.random_day_in_month(month_start, rng, lo=1)
    confirm = ordered + timedelta(days=rng.randint(0, 3))
    if confirm.month != ordered.month:
        confirm = date(ordered.year, ordered.month, tu.days_in_month(month_start))
    return (
        tu.datetime_at(ordered, hour=rng.randint(9, 17), minute=rng.choice([0, 15, 30, 45])),
        tu.datetime_at(confirm, hour=rng.randint(9, 17), minute=rng.choice([0, 15, 30, 45])),
    )


def _plan_one_so(
    customer: dict, month_start: date, rng: random.Random, *, big: bool = False
) -> PlannedSO | None:
    profile = stories.ROLE_PROFILES[customer["role"]]
    if big:
        big_range = tu.big_order_value_range(customer["code"]) or profile["avg_order_value"]
        target_value = Decimal(rng.randint(*big_range))
    else:
        target_value = Decimal(rng.randint(*profile["avg_order_value"]))
    margin_pct = rng.randint(*profile["target_margin_pct"])
    items = _build_items(target_value, margin_pct, list(profile["preferred_categories"]), month_start, rng)
    if not items:
        return None

    salesperson = tu.pick_salesperson(month_start, rng)
    ordered_dt, confirm_dt = _so_datetimes(month_start, rng)
    return PlannedSO(
        customer_code=customer["code"],
        salesperson_code=salesperson["code"],
        items=items,
        ordered_dt=ordered_dt,
        confirm_dt=confirm_dt,
        is_tax_inclusive=rng.random() < 0.20,
    )


def plan_all_sos(rng: random.Random) -> dict[date, list[PlannedSO]]:
    """Pass 1: build the full SO calendar without contacting the backend."""
    planned: dict[date, list[PlannedSO]] = defaultdict(list)
    for month_start in tu.month_iter(stories.TIMELINE_START, stories.TIMELINE_END):
        for customer in customers_cfg.CUSTOMERS:
            n = tu.customer_monthly_orders(customer, month_start, rng)
            for _ in range(n):
                so = _plan_one_so(customer, month_start, rng)
                if so is not None:
                    planned[month_start].append(so)
            # Big-order months stack one extra big SO on top of the baseline.
            if tu.is_big_order_month(customer["code"], month_start):
                so = _plan_one_so(customer, month_start, rng, big=True)
                if so is not None:
                    planned[month_start].append(so)
    return planned


def aggregate_po_demand(
    planned: dict[date, list[PlannedSO]]
) -> dict[date, dict[str, int]]:
    """{month_start → {sku → total planned units to sell this month}}."""
    demand: dict[date, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for month_start, sos in planned.items():
        for so in sos:
            for item in so.items:
                demand[month_start][item.sku] += item.quantity
    return demand


# ── EXECUTE PASS ─────────────────────────────────────────────────────


def _po_payload(
    supplier_id: int,
    items_by_sku: dict[str, int],
    state: SeedState,
    month_start: date,
    ordered_dt: datetime,
) -> dict[str, Any]:
    items_payload = []
    for sku, qty in items_by_sku.items():
        product = products_cfg.by_sku(sku)
        cost = (
            product["cost_price"]
            * tu.cumulative_cost_multiplier(sku, month_start)
        ).quantize(Decimal("0.01"))
        items_payload.append({
            "product_id": state.product_ids[sku],
            "quantity": qty,
            "unit_cost": str(cost),
        })
    return {
        "supplier_id": supplier_id,
        "is_tax_inclusive": False,
        "ordered_at": ordered_dt.isoformat(),
        "notes": f"seed PO {tu.year_month_key(month_start)}",
        "items": items_payload,
    }


def _backdate_po(
    client: SeedAPIClient,
    po_id: int,
    *,
    ordered_dt: datetime,
    received_dt: datetime,
    supplier_terms_days: int,
) -> None:
    # PO row: created_at / received_at / updated_at.
    client.backdate(
        "purchase_orders", po_id,
        created_at=ordered_dt,
        updated_at=received_dt,
        received_at=received_dt,
    )
    # AP row: issued_at / due_date / created_at.
    due = received_dt.date() + timedelta(days=supplier_terms_days)
    client.backdate_where(
        "accounts_payable", "purchase_order_id", po_id,
        issued_at=received_dt,
        due_date=due,
        created_at=received_dt,
        updated_at=received_dt,
    )


def _backdate_so(
    client: SeedAPIClient,
    so_id: int,
    *,
    ordered_dt: datetime,
    confirm_dt: datetime,
    customer_terms_days: int,
) -> None:
    client.backdate(
        "sales_orders", so_id,
        created_at=ordered_dt,
        updated_at=confirm_dt,
        confirmed_at=confirm_dt,
    )
    due = confirm_dt.date() + timedelta(days=customer_terms_days)
    client.backdate_where(
        "accounts_receivable", "sales_order_id", so_id,
        issued_at=confirm_dt,
        due_date=due,
        created_at=confirm_dt,
        updated_at=confirm_dt,
    )


def _po_for_supplier(
    sku_demand: dict[str, int], supplier_code: str, month_start: date
) -> dict[str, int]:
    """Per-supplier slice of demand for this month, plus a small safety buffer."""
    out: dict[str, int] = {}
    for sku, qty in sku_demand.items():
        product = products_cfg.by_sku(sku)
        if product["supplier_codes"][0] != supplier_code:
            continue
        # Add safety buffer + apply stockout severity.
        buffered = int((Decimal(qty) * (Decimal("1") + SAFETY_BUFFER_PCT)).quantize(Decimal("1")))
        sev = tu.stockout_severity(sku, month_start)
        if sev < Decimal("1"):
            buffered = max(0, int((Decimal(buffered) * sev).quantize(Decimal("1"))))
        if buffered > 0:
            out[sku] = buffered
    return out


def _force_cost_touch_skus(month_start: date) -> set[str]:
    """SKUs that have a hike active by this month — order at least 1 unit so
    the backend writes the hiked cost back to `product.cost_price`."""
    ym = tu.year_month_key(month_start)
    return {ev["sku"] for ev in stories.COST_HIKE_EVENTS if ev["effective_month"] <= ym}


def execute_month_pos(
    client: SeedAPIClient,
    state: SeedState,
    month_start: date,
    sku_demand: dict[str, int],
    rng: random.Random,
) -> int:
    """Create + receive POs for every supplier with demand this month. Returns count."""
    # Ensure cost-touched SKUs are present even if demand is zero this month.
    for touch_sku in _force_cost_touch_skus(month_start):
        sku_demand.setdefault(touch_sku, 1)

    pos_created = 0
    suppliers_with_demand = {
        products_cfg.by_sku(sku)["supplier_codes"][0]
        for sku in sku_demand
    }
    for supplier_code in suppliers_with_demand:
        items = _po_for_supplier(sku_demand, supplier_code, month_start)
        if not items:
            continue
        supplier_id = state.supplier_ids[supplier_code]
        supplier_cfg = suppliers_cfg.by_code(supplier_code)

        ordered_dt = tu.datetime_at(
            tu.random_day_in_month(month_start, rng, lo=1, hi=5), hour=10
        )
        # Receive a few days after order, capped to month end so analytics buckets cleanly.
        rec_day = min(ordered_dt.day + rng.randint(2, 7), tu.days_in_month(month_start))
        received_dt = tu.datetime_at(
            date(month_start.year, month_start.month, rec_day), hour=14
        )

        payload = _po_payload(supplier_id, items, state, month_start, ordered_dt)
        po = client.post("/purchase-orders", json=payload).json()
        po_id = po["id"]
        client.post(f"/purchase-orders/{po_id}/receive")
        _backdate_po(
            client, po_id,
            ordered_dt=ordered_dt,
            received_dt=received_dt,
            supplier_terms_days=supplier_cfg["payment_terms_days"],
        )
        pos_created += 1
    return pos_created


def execute_month_sos(
    client: SeedAPIClient,
    state: SeedState,
    month_start: date,
    sos: list[PlannedSO],
    rng: random.Random,
) -> tuple[int, int]:
    """Create + confirm each planned SO. Returns (confirmed, skipped)."""
    confirmed = skipped = 0
    for so in sos:
        customer_id = state.customer_ids[so.customer_code]
        salesperson_id = state.user_ids[so.salesperson_code]
        customer_cfg = customers_cfg.by_code(so.customer_code)

        items_payload = [
            {
                "product_id": state.product_ids[item.sku],
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
            }
            for item in so.items
        ]
        payload = {
            "customer_id": customer_id,
            "salesperson_id": salesperson_id,
            "is_tax_inclusive": so.is_tax_inclusive,
            "ordered_at": so.ordered_dt.isoformat(),
            "notes": f"seed SO {tu.year_month_key(month_start)}",
            "items": items_payload,
        }
        try:
            draft = client.post("/sales-orders", json=payload).json()
        except SeedAPIError:
            skipped += 1
            continue
        so_id = draft["id"]
        try:
            client.post(f"/sales-orders/{so_id}/confirm")
        except SeedAPIError:
            # Stock shortage — halve and retry by patching the draft.
            halved_items = []
            for it in items_payload:
                q = max(1, int(it["quantity"]) // 2)
                halved_items.append({**it, "quantity": q})
            try:
                client.patch(
                    f"/sales-orders/{so_id}",
                    json={"items": halved_items},
                )
                client.post(f"/sales-orders/{so_id}/confirm")
            except SeedAPIError:
                # Still failing → cancel and skip.
                try:
                    client.post(f"/sales-orders/{so_id}/cancel")
                except SeedAPIError:
                    pass
                skipped += 1
                continue

        _backdate_so(
            client, so_id,
            ordered_dt=so.ordered_dt,
            confirm_dt=so.confirm_dt,
            customer_terms_days=customer_cfg["payment_terms_days"],
        )
        confirmed += 1
    return confirmed, skipped


# ── ENTRY POINT ──────────────────────────────────────────────────────


def run_timeline(client: SeedAPIClient, state: SeedState) -> None:
    """Plan and execute the 18-month timeline against the backend.

    Refuses to run if PO/SO rows already exist — re-running on top of an
    existing dataset would double everything. Use ``--reset`` to wipe first.
    """
    existing_pos = client.get(
        "/purchase-orders", params={"limit": 1}
    ).json()
    existing_sos = client.get(
        "/sales-orders", params={"limit": 1}
    ).json()
    if existing_pos or existing_sos:
        raise RuntimeError(
            "[timeline] refuse to run: PO/SO rows already exist in seed.db. "
            "Re-run with --reset to wipe transactional data first, or use "
            "--stop-after catalog to skip the timeline step."
        )

    rng = random.Random(tu.RNG_SEED)

    print("[timeline] planning all SOs in memory ...")
    planned = plan_all_sos(rng)
    total_sos = sum(len(v) for v in planned.values())
    print(f"[timeline]   planned {total_sos} SOs across {len(planned)} months")
    demand = aggregate_po_demand(planned)

    total_pos = total_confirmed = total_skipped = 0
    for month_start in tu.month_iter(stories.TIMELINE_START, stories.TIMELINE_END):
        ym = tu.year_month_key(month_start)
        sku_demand = dict(demand.get(month_start, {}))
        sos = planned.get(month_start, [])

        pos_this_month = execute_month_pos(client, state, month_start, sku_demand, rng)
        # Sort SOs by ordered_dt so the in-DB created_at order roughly matches story time.
        sos_sorted = sorted(sos, key=lambda s: s.ordered_dt)
        confirmed, skipped = execute_month_sos(client, state, month_start, sos_sorted, rng)

        total_pos += pos_this_month
        total_confirmed += confirmed
        total_skipped += skipped
        print(
            f"[timeline] {ym}: PO={pos_this_month} "
            f"SO confirmed={confirmed} skipped={skipped}"
        )

    print(
        f"[timeline] done: {total_pos} POs, "
        f"{total_confirmed} SOs confirmed, {total_skipped} skipped"
    )
