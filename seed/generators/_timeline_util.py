"""Shared helpers for the timeline generator.

The timeline walks 18 months in deterministic order. Anything stochastic
goes through ``rng`` so reruns are reproducible.
"""
from __future__ import annotations

import calendar
import random
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Iterable

from seed.config import people as people_cfg
from seed.config import stories


# Fixed RNG seed so the dataset is reproducible across runs / machines.
RNG_SEED = 20260522


def month_iter(start: date, end: date) -> Iterable[date]:
    """Yield the first day of every month from ``start`` to ``end`` inclusive."""
    cur = date(start.year, start.month, 1)
    last = date(end.year, end.month, 1)
    while cur <= last:
        yield cur
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)


def year_month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def quarter_of(d: date) -> int:
    return (d.month - 1) // 3 + 1


def days_in_month(d: date) -> int:
    return calendar.monthrange(d.year, d.month)[1]


def datetime_at(d: date, hour: int = 10, minute: int = 0) -> datetime:
    """Build a timezone-aware UTC datetime for SQL backdate / ordered_at."""
    return datetime.combine(d, time(hour, minute), tzinfo=timezone.utc)


def random_day_in_month(month_start: date, rng: random.Random, *, lo: int = 1, hi: int | None = None) -> date:
    """Pick a random day-of-month, clamped to days_in_month."""
    upper = hi if hi is not None else days_in_month(month_start)
    day = rng.randint(lo, min(upper, days_in_month(month_start)))
    return date(month_start.year, month_start.month, day)


# ── salesperson weighting ────────────────────────────────────────────

_BASE_TIER_WEIGHT = {
    "star": Decimal("4.0"),
    "mid": Decimal("2.0"),
    "average": Decimal("1.0"),
    "declining": Decimal("1.3"),  # before personal multipliers kick in
    "newbie": Decimal("0.4"),
}


def _personal_multiplier(person_code: str, year_month: str) -> Decimal:
    """Combined multiplier from all SALES_PERSONAL_EVENTS for this person/month."""
    m = Decimal("1")
    for ev in stories.SALES_PERSONAL_EVENTS:
        if ev["person_code"] == person_code and year_month in ev["months"]:
            m *= ev["multiplier"]
    return m


def is_employee_active(person: dict, ref: date) -> bool:
    """True if ``person`` is hired (by ref) and not terminated."""
    if person.get("hire_date") and person["hire_date"] > ref:
        return False
    term = person.get("termination_date")
    if term and term <= ref:
        return False
    return True


def active_sales_weights(month_start: date) -> list[tuple[dict, Decimal]]:
    """Active sales staff for the given month with their effective weight.

    A weight of 0 means "don't pick them this month" (e.g. newbie pre-hire,
    declining #3 at zero multiplier). Step 4 filters those out before sampling.
    """
    ym = year_month_key(month_start)
    out: list[tuple[dict, Decimal]] = []
    for p in people_cfg.SALES:
        if not is_employee_active(p, month_start):
            continue
        base = _BASE_TIER_WEIGHT[p.get("tier", "average")]
        weight = base * _personal_multiplier(p["code"], ym)
        out.append((p, weight))
    return out


def pick_salesperson(month_start: date, rng: random.Random) -> dict:
    """Tier-weighted salesperson sample for this month."""
    weighted = [(p, w) for p, w in active_sales_weights(month_start) if w > 0]
    if not weighted:
        raise RuntimeError(f"no active sales staff in {month_start}")
    population = [p for p, _ in weighted]
    weights = [float(w) for _, w in weighted]
    return rng.choices(population, weights=weights, k=1)[0]


# ── customer monthly-order modulation ────────────────────────────────


def _override_for(customer_code: str) -> stories.CustomerStoryOverride | None:
    for ov in stories.CUSTOMER_STORY_OVERRIDES:
        if ov.get("code") == customer_code:
            return ov
    return None


def customer_active(customer_code: str, month_start: date) -> bool:
    ov = _override_for(customer_code)
    if ov is None:
        return True
    window = ov.get("active_window")
    if window is None:
        return True
    lo, hi = window
    return lo <= year_month_key(month_start) <= hi


def customer_monthly_orders(
    customer: dict, month_start: date, rng: random.Random
) -> int:
    """Sample # of SOs to generate for this customer this month."""
    if not customer_active(customer["code"], month_start):
        return 0

    profile = stories.ROLE_PROFILES[customer["role"]]
    ym = year_month_key(month_start)
    q = quarter_of(month_start)
    ov = _override_for(customer["code"]) or {}

    # 1. Base monthly orders — overrides win when present for this month.
    if ym in ov.get("monthly_orders_override", {}):
        lo, hi = ov["monthly_orders_override"][ym]
    elif "quarterly_burst" in ov and ov["quarterly_burst"][0] == q:
        lo, hi = ov["quarterly_burst"][1]
    else:
        lo, hi = profile["monthly_orders"]
    n = rng.randint(lo, hi)

    # 2. Seasonality (skip when the customer override already sets the count).
    if ym not in ov.get("monthly_orders_override", {}):
        mult = stories.QUARTERLY_MULTIPLIERS[q]
        # Stochastic rounding — apply the float multiplier and round.
        n = int(round(n * float(mult)))

    # 3. Compounded monthly growth (e.g. XINMAO_AI +30%/month).
    if "growth_start_month" in ov and "monthly_growth_pct" in ov:
        start_ym = ov["growth_start_month"]
        if ym >= start_ym:
            months_in = _months_between(start_ym, ym)
            growth = float(ov["monthly_growth_pct"]) ** months_in
            n = int(round(n * growth))

    # 4. Big-order months contribute +1 large order (handled in SO loop).
    return max(n, 0)


def _months_between(ym_lo: str, ym_hi: str) -> int:
    """Inclusive lower-bound, exclusive upper-bound count of months."""
    lo_y, lo_m = int(ym_lo[:4]), int(ym_lo[5:])
    hi_y, hi_m = int(ym_hi[:4]), int(ym_hi[5:])
    return max(0, (hi_y - lo_y) * 12 + (hi_m - lo_m))


def is_big_order_month(customer_code: str, month_start: date) -> bool:
    ov = _override_for(customer_code)
    if ov is None:
        return False
    return year_month_key(month_start) in ov.get("big_order_months", [])


def big_order_value_range(customer_code: str) -> tuple[int, int] | None:
    ov = _override_for(customer_code)
    if ov is None:
        return None
    return ov.get("big_order_value")


# ── cost hike + stockout lookups ─────────────────────────────────────


def cumulative_cost_multiplier(sku: str, month_start: date) -> Decimal:
    """Compound all COST_HIKE_EVENTS with effective_month <= this month."""
    ym = year_month_key(month_start)
    m = Decimal("1")
    for ev in stories.COST_HIKE_EVENTS:
        if ev["sku"] == sku and ev["effective_month"] <= ym:
            m *= ev["cost_multiplier"]
    return m


def stockout_severity(sku: str, month_start: date) -> Decimal:
    """1.0 = normal restock; <1.0 = reduced this month."""
    ym = year_month_key(month_start)
    for ev in stories.STOCKOUT_EVENTS:
        if ev["sku"] == sku and ym in ev["months"]:
            return ev["severity"]
    return Decimal("1")
