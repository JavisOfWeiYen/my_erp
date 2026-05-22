"""Events generator (Step 5): scripted post-timeline mutations.

Four sub-steps run in order:

1. **Stock adjustments** — 6 scripted `STOCK_ADJUST_EVENTS` (damage / count
   loss / count gain). POST `/stock-adjustments`, then backdate
   `adjusted_at` / `created_at` into the event month.
2. **AR payments** — walk every AR row, sample per customer role profile
   to decide whether & when to pay. `paid_at` is honoured by the API
   payload, so no SQL backdate is needed for that field.
3. **AP payments** — pay every AP on time (1-5 days before due). Suppliers
   aren't a demo subject; no overdue drama.
4. **Payment voids** — 2 scripted `PAYMENT_VOID_EVENTS` (誤入帳 / 退票).
   Find a matching payment in the event month, void via API.

Together these turn the open-only AR ledger left by Step 4 into a
realistic mix of paid / partial / overdue + 2 voided records, matching
the storylines in `seed/STORYLINES.md`.
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from decimal import Decimal

from seed.config import customers as customers_cfg
from seed.config import stories

from . import _timeline_util as tu
from .api_client import SeedAPIClient, SeedAPIError
from .seed_setup import SeedState


# Cap any backdated paid_at to "today" so we never produce future-dated
# payments. Matches the timeline window's natural endpoint.
PAID_AT_CEILING = date(2026, 5, 22)


# ── stock adjustment reason mapping (config → backend enum) ──────────
# config side uses richer vocabulary; backend has 4 canonical values.
STOCK_REASON_MAP: dict[str, str] = {
    "damage": "scrap",
    "count_loss": "shortage",
    "count_gain": "surplus",
    "sample": "other",
    "other": "other",
}


# ── AR payment timing profiles per customer role ─────────────────────
# Each role has either:
#   - `lateness`: a single (lo, hi) days offset from due_date, OR
#   - `late_split`: list of (probability, (lo, hi)) — sample one bucket
#                    and pick within its range.
# Negative offsets = pay before due; positive = pay after due.
#
# `pay_rate` = probability the AR ever gets paid (vs. left open forever).

PAYMENT_PROFILE_BY_ROLE: dict[str, dict] = {
    "vip_stable":      {"pay_rate": 1.00, "lateness": (-10, -1)},
    "vip_volume":      {"pay_rate": 1.00, "late_split": [(0.85, (-3, 5)), (0.15, (10, 30))]},
    "churn":           {"pay_rate": 0.80, "late_split": [(0.40, (-3, 5)), (0.60, (15, 60))]},
    "hard_negotiator": {"pay_rate": 1.00, "late_split": [(0.90, (-2, 2)), (0.10, (5, 20))]},
    "overdue":         {"pay_rate": 0.70, "late_split": [(0.15, (-1, 10)), (0.85, (45, 100))]},
    "seasonal":        {"pay_rate": 1.00, "late_split": [(0.90, (-3, 0)), (0.10, (5, 15))]},
    "rising":          {"pay_rate": 1.00, "lateness": (-5, 0)},
    "academic":        {"pay_rate": 1.00, "late_split": [(0.80, (-2, 5)), (0.20, (15, 45))]},
    "regional_dealer": {"pay_rate": 1.00, "late_split": [(0.90, (-3, 3)), (0.10, (5, 20))]},
    "ai_cloud":        {"pay_rate": 1.00, "late_split": [(0.95, (-5, 0)), (0.05, (5, 15))]},
    "sporadic":        {"pay_rate": 1.00, "late_split": [(0.90, (-3, 5)), (0.10, (10, 30))]},
    "background":      {"pay_rate": 1.00, "late_split": [(0.85, (-3, 3)), (0.15, (5, 25))]},
}


def _pick_payment_offset(
    role: str, customer_code: str, issued_month: str, rng: random.Random
) -> int | None:
    """Return days-from-due offset, or None to skip payment entirely."""
    profile = PAYMENT_PROFILE_BY_ROLE.get(role, PAYMENT_PROFILE_BY_ROLE["background"])

    # XIANGFENG override: from 2026-03 onwards drops to 30% pay rate
    # (escalating the churn story — they stop paying when they stop ordering).
    if customer_code == "XIANGFENG_PC" and issued_month >= "2026-03":
        if rng.random() > 0.30:
            return None

    if rng.random() > profile["pay_rate"]:
        return None

    if "lateness" in profile:
        return rng.randint(*profile["lateness"])

    # Sample from a discrete distribution of (probability, range) buckets.
    splits = profile["late_split"]
    r = rng.random()
    cum = 0.0
    for prob, span in splits:
        cum += prob
        if r < cum:
            return rng.randint(*span)
    return rng.randint(*splits[-1][1])


def _reverse_lookup(state_dict: dict[str, int]) -> dict[int, str]:
    return {v: k for k, v in state_dict.items()}


# ── stock adjustments ────────────────────────────────────────────────


def seed_stock_adjustments(
    client: SeedAPIClient, state: SeedState, rng: random.Random
) -> int:
    n = 0
    for ev in stories.STOCK_ADJUST_EVENTS:
        sku = ev["sku"]
        if sku not in state.product_ids:
            print(f"  [adj] skip {sku} (no product registered)")
            continue
        backend_reason = STOCK_REASON_MAP.get(ev["reason"], "other")
        payload = {
            "product_id": state.product_ids[sku],
            "change_qty": ev["quantity_delta"],
            "reason": backend_reason,
            "notes": ev["note"],
        }
        try:
            adj = client.post("/stock-adjustments", json=payload).json()
        except SeedAPIError as e:
            print(f"  [adj] FAILED {sku} {ev['month']}: {e}")
            continue

        # Backdate adjusted_at + created_at into the event's month.
        ym = ev["month"]
        year, month = int(ym[:4]), int(ym[5:])
        day = rng.randint(1, tu.days_in_month(date(year, month, 1)))
        dt = tu.datetime_at(date(year, month, day), hour=rng.randint(9, 17))
        client.backdate(
            "stock_adjustments", adj["id"],
            adjusted_at=dt,
            created_at=dt,
        )
        n += 1
    return n


# ── AR payments ──────────────────────────────────────────────────────


def _paginate(client: SeedAPIClient, path: str, **extra) -> list[dict]:
    """Walk a paginated list endpoint until exhausted."""
    out: list[dict] = []
    skip = 0
    while True:
        batch = client.get(path, params={"skip": skip, "limit": 100, **extra}).json()
        if not batch:
            break
        out.extend(batch)
        if len(batch) < 100:
            break
        skip += 100
    return out


def seed_ar_payments(
    client: SeedAPIClient, state: SeedState, rng: random.Random
) -> tuple[int, int]:
    print("[events] fetching all AR rows ...")
    ars = _paginate(client, "/accounts-receivable")
    print(f"[events]   {len(ars)} AR rows fetched")

    cust_by_id = _reverse_lookup(state.customer_ids)
    paid = unpaid = 0
    for ar in ars:
        customer_code = cust_by_id.get(ar["customer_id"])
        if not customer_code:
            unpaid += 1
            continue
        role = customers_cfg.by_code(customer_code)["role"]
        issued_dt = datetime.fromisoformat(ar["issued_at"].replace("Z", "+00:00"))
        issued_month = f"{issued_dt.year:04d}-{issued_dt.month:02d}"

        offset = _pick_payment_offset(role, customer_code, issued_month, rng)
        if offset is None:
            unpaid += 1
            continue

        due = date.fromisoformat(ar["due_date"])
        paid_date = due + timedelta(days=offset)
        # Clamp: never future, never before invoice issued.
        paid_date = min(paid_date, PAID_AT_CEILING)
        paid_date = max(paid_date, issued_dt.date())

        paid_at = tu.datetime_at(
            paid_date,
            hour=rng.randint(9, 17),
            minute=rng.choice([0, 15, 30, 45]),
        )
        payload = {
            "accounts_receivable_id": ar["id"],
            "amount": str(Decimal(ar["amount_total"])),
            "method": rng.choices(
                ["bank_transfer", "check", "cash"], weights=[8, 2, 1], k=1
            )[0],
            "paid_at": paid_at.isoformat(),
        }
        try:
            client.post("/ar-payments", json=payload)
            paid += 1
        except SeedAPIError:
            unpaid += 1
    return paid, unpaid


# ── AP payments ──────────────────────────────────────────────────────


def seed_ap_payments(
    client: SeedAPIClient, state: SeedState, rng: random.Random
) -> int:
    print("[events] fetching all AP rows ...")
    aps = _paginate(client, "/accounts-payable")
    print(f"[events]   {len(aps)} AP rows fetched")
    paid = 0
    for ap in aps:
        due = date.fromisoformat(ap["due_date"])
        offset = rng.randint(-5, 0)  # 0-5 days early
        paid_date = due + timedelta(days=offset)
        paid_date = min(paid_date, PAID_AT_CEILING)
        issued_date = datetime.fromisoformat(
            ap["issued_at"].replace("Z", "+00:00")
        ).date()
        paid_date = max(paid_date, issued_date)
        paid_at = tu.datetime_at(paid_date, hour=rng.randint(9, 16))
        payload = {
            "accounts_payable_id": ap["id"],
            "amount": str(Decimal(ap["amount_total"])),
            "method": "bank_transfer",
            "paid_at": paid_at.isoformat(),
        }
        try:
            client.post("/ap-payments", json=payload)
            paid += 1
        except SeedAPIError:
            pass
    return paid


# ── Payment voids ────────────────────────────────────────────────────


def seed_payment_voids(client: SeedAPIClient, state: SeedState) -> int:
    n = 0
    for ev in stories.PAYMENT_VOID_EVENTS:
        if ev["kind"] != "ar":
            continue
        customer_code = ev["party_code"]
        customer_id = state.customer_ids.get(customer_code)
        if customer_id is None:
            continue

        ars = client.get(
            "/accounts-receivable",
            params={"customer_id": customer_id, "limit": 200},
        ).json()
        target_payment = None
        for ar in ars:
            payments = client.get(
                "/ar-payments",
                params={"accounts_receivable_id": ar["id"]},
            ).json()
            for p in payments:
                pdt = datetime.fromisoformat(p["paid_at"].replace("Z", "+00:00"))
                ym = f"{pdt.year:04d}-{pdt.month:02d}"
                if ym == ev["month"] and not p.get("voided_at"):
                    target_payment = p
                    break
            if target_payment:
                break

        if not target_payment:
            print(f"  [void] no AR payment matched {customer_code} in {ev['month']}")
            continue

        client.post(
            f"/ar-payments/{target_payment['id']}/void",
            json={"reason": ev["reason"]},
        )
        n += 1
    return n


# ── Entry ────────────────────────────────────────────────────────────


def run_events(client: SeedAPIClient, state: SeedState) -> None:
    """Apply scripted post-timeline events. See STORYLINES.md for context."""
    rng = random.Random(tu.RNG_SEED + 1)  # different stream than the timeline

    print("[events] applying scripted stock adjustments ...")
    n_adj = seed_stock_adjustments(client, state, rng)
    print(f"[events]   stock adjustments: {n_adj}")

    print("[events] generating AR payments ...")
    paid_ar, unpaid_ar = seed_ar_payments(client, state, rng)
    print(f"[events]   AR: {paid_ar} paid, {unpaid_ar} left open")

    print("[events] generating AP payments ...")
    paid_ap = seed_ap_payments(client, state, rng)
    print(f"[events]   AP: {paid_ap} paid")

    print("[events] applying scripted AR payment voids ...")
    n_voids = seed_payment_voids(client, state)
    print(f"[events]   payment voids: {n_voids}")
