"""Storyline configuration — quarterly multipliers + 12+ scripted events.

The Step 4 / Step 5 generators read three layers per month:

1. `QUARTERLY_MULTIPLIERS[quarter]`         — base seasonality
2. `ROLE_PROFILES[customer.role]`           — default volume / margin /
                                              cadence per archetype
3. event lists in this file (cost hikes,
   personal events, churn windows, stockouts,
   stock adjustments, payment voids, etc.)  — scripted exceptions

Keeping the cadence inside ROLE_PROFILES (rather than per-customer rows)
keeps the static config short and lets Step 4 mix in randomness. The
12 specifically-scripted events still get explicit rows so the demo
acceptance criteria are reproducible.

All dates are ISO YYYY-MM-DD or YYYY-MM (month bucket). The timeline
window is `TIMELINE_START` .. `TIMELINE_END`, inclusive.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Final, Literal, TypedDict


# ── Timeline window ──────────────────────────────────────────────────
TIMELINE_START: Final[date] = date(2024, 12, 1)
TIMELINE_END: Final[date] = date(2026, 5, 31)


# ── Seasonality ──────────────────────────────────────────────────────
QUARTERLY_MULTIPLIERS: Final[dict[int, Decimal]] = {
    1: Decimal("0.90"),  # 春節後淡季
    2: Decimal("1.00"),  # 平穩
    3: Decimal("0.95"),  # 暑假淡
    4: Decimal("1.35"),  # Q4 旺季（年底電競 / 雙 11 / 預算花用）
}


# ── Customer role baseline profiles ──────────────────────────────────
# Used by Step 4 as default behaviour per customer; individual exceptions
# live in CUSTOMER_STORY_OVERRIDES below.
CategoryCode = Literal[
    "GPU_CONSUMER_NV",
    "GPU_CONSUMER_AMD",
    "GPU_WORKSTATION",
    "GPU_DATACENTER",
    "AI_SERVER",
]


class RoleProfile(TypedDict):
    monthly_orders: tuple[int, int]      # (min, max) draws per month
    avg_order_value: tuple[int, int]     # NTD, per order (pre-tax baseline)
    target_margin_pct: tuple[int, int]   # %; Step 4 nudges unit_price to hit
    preferred_categories: list[CategoryCode]
    overdue_rate: Decimal                # 0~1, prob. of paying past due
    notes: str


ROLE_PROFILES: Final[dict[str, RoleProfile]] = {
    "vip_stable": {
        "monthly_orders": (5, 7),
        "avg_order_value": (300_000, 1_200_000),
        "target_margin_pct": (12, 18),
        "preferred_categories": ["GPU_DATACENTER", "AI_SERVER", "GPU_WORKSTATION"],
        "overdue_rate": Decimal("0.00"),
        "notes": "大同雲端 — 從未逾期",
    },
    "vip_volume": {
        "monthly_orders": (4, 6),
        "avg_order_value": (500_000, 1_500_000),
        "target_margin_pct": (8, 12),
        "preferred_categories": ["GPU_DATACENTER", "GPU_WORKSTATION", "AI_SERVER"],
        "overdue_rate": Decimal("0.15"),
        "notes": "泰昌 — 大買家但毛利薄",
    },
    "churn": {
        "monthly_orders": (5, 8),
        "avg_order_value": (80_000, 250_000),
        "target_margin_pct": (15, 20),
        "preferred_categories": ["GPU_CONSUMER_NV", "GPU_CONSUMER_AMD", "GPU_WORKSTATION"],
        "overdue_rate": Decimal("0.60"),
        "notes": "祥豐 — 2026-03 後跌；歷史逾期 60%",
    },
    "hard_negotiator": {
        "monthly_orders": (4, 6),
        "avg_order_value": (150_000, 400_000),
        "target_margin_pct": (5, 9),
        "preferred_categories": ["GPU_CONSUMER_NV", "GPU_CONSUMER_AMD", "GPU_WORKSTATION"],
        "overdue_rate": Decimal("0.10"),
        "notes": "和欣 — 議價兇毛利薄",
    },
    "overdue": {
        "monthly_orders": (1, 3),
        "avg_order_value": (40_000, 120_000),
        "target_margin_pct": (15, 22),
        "preferred_categories": ["GPU_CONSUMER_NV", "GPU_CONSUMER_AMD"],
        "overdue_rate": Decimal("0.85"),
        "notes": "旭光 — 金額不大但每筆都壓滿 60 天",
    },
    "seasonal": {
        "monthly_orders": (0, 1),  # Q4 用 monthly_orders_q4_override
        "avg_order_value": (200_000, 500_000),
        "target_margin_pct": (16, 22),
        "preferred_categories": ["GPU_CONSUMER_NV"],
        "overdue_rate": Decimal("0.10"),
        "notes": "宏億 — 只 Q4 出現；Q1-Q3 1 單以下",
    },
    "rising": {
        "monthly_orders": (1, 2),   # ramps via CUSTOMER_STORY_OVERRIDES
        "avg_order_value": (600_000, 2_500_000),
        "target_margin_pct": (10, 16),
        "preferred_categories": ["GPU_DATACENTER", "AI_SERVER"],
        "overdue_rate": Decimal("0.10"),
        "notes": "新茂 AI — 2026-01 起、每月成長；主買 H100 + AI 整機",
    },
    "academic": {
        "monthly_orders": (0, 1),   # 季度型 — 用 quarterly_burst 補
        "avg_order_value": (300_000, 1_500_000),
        "target_margin_pct": (22, 30),
        "preferred_categories": ["GPU_WORKSTATION", "GPU_DATACENTER", "AI_SERVER"],
        "overdue_rate": Decimal("0.20"),
        "notes": "慧林 / 慧達 — 季度大單、毛利最高",
    },
    "regional_dealer": {
        "monthly_orders": (3, 8),
        "avg_order_value": (80_000, 300_000),
        "target_margin_pct": (12, 18),
        "preferred_categories": ["GPU_CONSUMER_NV", "GPU_CONSUMER_AMD", "GPU_WORKSTATION"],
        "overdue_rate": Decimal("0.10"),
        "notes": "聖光資訊 — 區域中盤通路；下游再賣給小型 SI",
    },
    "ai_cloud": {
        "monthly_orders": (3, 6),
        "avg_order_value": (1_500_000, 8_000_000),
        "target_margin_pct": (12, 18),
        "preferred_categories": ["GPU_DATACENTER", "AI_SERVER"],
        "overdue_rate": Decimal("0.05"),
        "notes": "立通 — 雲服務商；AI 熱潮主力買 H100 整機 + 卡",
    },
    "sporadic": {
        "monthly_orders": (0, 1),   # 大單透過 big_order_months
        "avg_order_value": (100_000, 300_000),
        "target_margin_pct": (14, 20),
        "preferred_categories": ["GPU_CONSUMER_NV", "GPU_WORKSTATION", "AI_SERVER"],
        "overdue_rate": Decimal("0.10"),
        "notes": "達銘 — 每 3-4 月一張極大單",
    },
    "background": {
        "monthly_orders": (1, 4),
        "avg_order_value": (60_000, 350_000),
        "target_margin_pct": (15, 22),
        "preferred_categories": ["GPU_CONSUMER_NV", "GPU_CONSUMER_AMD", "GPU_WORKSTATION"],
        "overdue_rate": Decimal("0.15"),
        "notes": "背景戶 — 正常分布；中盤通路 + 小型 SI 為主",
    },
}


# ── Per-customer scripted overrides ──────────────────────────────────
class CustomerStoryOverride(TypedDict, total=False):
    code: str                                     # customer code
    active_window: tuple[str, str]                # ("YYYY-MM", "YYYY-MM"), inclusive
    monthly_orders_override: dict[str, tuple[int, int]]
    monthly_growth_pct: Decimal                   # multiplier per month after start
    growth_start_month: str                       # "YYYY-MM"
    quarterly_burst: tuple[int, tuple[int, int]]  # (Q, (min, max)) — Q only
    big_order_months: list[str]                   # months in which to add 1 extra big order
    big_order_value: tuple[int, int]              # NTD range for those big orders
    notes: str


CUSTOMER_STORY_OVERRIDES: Final[list[CustomerStoryOverride]] = [
    {
        "code": "XIANGFENG_PC",
        "monthly_orders_override": {
            "2026-03": (1, 2),
            "2026-04": (0, 1),
            "2026-05": (0, 1),
        },
        "notes": "2026-03 起流失：6+ 單 → 1 單",
    },
    {
        "code": "XINMAO_AI",
        "active_window": ("2026-01", "2026-05"),
        "growth_start_month": "2026-01",
        "monthly_growth_pct": Decimal("1.30"),  # +30% / month compounded
        "notes": "2026-01 入場、月增 30%",
    },
    {
        "code": "LITONG_TECH",
        "monthly_orders_override": {
            "2025-10": (1, 2),
            "2025-11": (0, 1),
            "2025-12": (0, 1),
            "2026-01": (0, 1),
            "2026-02": (0, 1),
            "2026-03": (0, 1),
            "2026-04": (0, 0),
            "2026-05": (0, 0),
        },
        "notes": "AI 熱潮 2025-Q4 後沉寂",
    },
    {
        "code": "HONGYI_CH",
        "quarterly_burst": (4, (5, 8)),
        "notes": "Q4 大量採購；其他季幾乎不出現",
    },
    {
        "code": "HUILIN_RES",
        "quarterly_burst": (1, (2, 3)),
        "notes": "季度集中採購",
    },
    {
        "code": "BG_HUIDA_UNI",
        "quarterly_burst": (1, (1, 2)),
        "notes": "學術；季度採購流程慢",
    },
    {
        "code": "DAMING_ELEC",
        "big_order_months": ["2025-03", "2025-07", "2025-11", "2026-03"],
        "big_order_value": (800_000, 1_800_000),
        "notes": "每 3-4 月一張極大單",
    },
]


# ── Sales personal events ────────────────────────────────────────────
class SalesPersonalEvent(TypedDict):
    person_code: str
    months: list[str]           # ["YYYY-MM", ...]
    multiplier: Decimal         # applied on top of weekly base weight
    note: str


SALES_PERSONAL_EVENTS: Final[list[SalesPersonalEvent]] = [
    # 明星 #2 病假
    {
        "person_code": "SLS_STAR_2",
        "months": ["2025-08", "2025-09"],
        "multiplier": Decimal("0.20"),
        "note": "李曉雯病假兩個月",
    },
    {
        "person_code": "SLS_STAR_2",
        "months": ["2025-10"],
        "multiplier": Decimal("0.75"),
        "note": "病假後恢復中",
    },
    # 明星 #1 AI 熱潮加成（負責立通）
    {
        "person_code": "SLS_STAR_1",
        "months": ["2025-01", "2025-02", "2025-03"],
        "multiplier": Decimal("1.40"),
        "note": "H100 AI 熱潮、立通狂掃帶飛業績",
    },
    # 衰退軌跡
    {
        "person_code": "SLS_DECLINE_1",
        "months": ["2025-07", "2025-08", "2025-09"],
        "multiplier": Decimal("0.85"),
        "note": "黃秀美 業績輕度下滑",
    },
    {
        "person_code": "SLS_DECLINE_1",
        "months": ["2025-10", "2025-11", "2025-12"],
        "multiplier": Decimal("0.70"),
        "note": "黃秀美 持續下滑",
    },
    {
        "person_code": "SLS_DECLINE_1",
        "months": ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05"],
        "multiplier": Decimal("0.50"),
        "note": "黃秀美 只剩維護單",
    },
    {
        "person_code": "SLS_DECLINE_2",
        "months": ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05"],
        "multiplier": Decimal("0.50"),
        "note": "吳建華 跟和欣衝突丟客戶",
    },
    {
        "person_code": "SLS_DECLINE_3",
        "months": ["2026-04", "2026-05"],
        "multiplier": Decimal("0.00"),
        "note": "劉雅婷 已不開單（疑似離職前夕）",
    },
    # 新人崛起
    {
        "person_code": "SLS_NEWBIE",
        "months": ["2026-01"],
        "multiplier": Decimal("0.40"),
        "note": "蔡明軒 入職首月、慢熱",
    },
    {
        "person_code": "SLS_NEWBIE",
        "months": ["2026-02", "2026-03"],
        "multiplier": Decimal("0.80"),
        "note": "蔡明軒 跟單熟悉中",
    },
    {
        "person_code": "SLS_NEWBIE",
        "months": ["2026-04", "2026-05"],
        "multiplier": Decimal("2.50"),
        "note": "蔡明軒 爆發、月 8+ 單挑戰中段班",
    },
]


# ── Cost-price hike events ───────────────────────────────────────────
# Applied as a multiplier on `product.cost_price` for PO received in that
# month or later (until a subsequent event overrides). Sales-side
# `unit_price` follows via target_margin_pct.
class CostHikeEvent(TypedDict):
    sku: str
    effective_month: str        # "YYYY-MM"
    cost_multiplier: Decimal    # vs. current cost_price
    supplier_code: str          # source supplier triggering the hike
    note: str


COST_HIKE_EVENTS: Final[list[CostHikeEvent]] = [
    # NVIDIA 區域配額調整 + 定價上修（S5 demo 主軸）— 連續 2 月、每月 20%
    # 影響 SKU：NV-5070 / NV-5070TI / NV-4080S / NV-4070S。累積 1.20 × 1.20 = 1.44
    # （與真實 2025 NVIDIA 配額緊縮時通路進價反映幅度一致）。
    {"sku": "NV-5070",   "effective_month": "2026-04", "cost_multiplier": Decimal("1.20"), "supplier_code": "NVIDIA", "note": "NVIDIA 區域配額調整、4 月進價上修 20%"},
    {"sku": "NV-5070TI", "effective_month": "2026-04", "cost_multiplier": Decimal("1.20"), "supplier_code": "NVIDIA", "note": "NVIDIA 區域配額調整、4 月進價上修 20%"},
    {"sku": "NV-4080S",  "effective_month": "2026-04", "cost_multiplier": Decimal("1.20"), "supplier_code": "NVIDIA", "note": "NVIDIA 區域配額調整、4 月進價上修 20%"},
    {"sku": "NV-4070S",  "effective_month": "2026-04", "cost_multiplier": Decimal("1.20"), "supplier_code": "NVIDIA", "note": "NVIDIA 區域配額調整、4 月進價上修 20%"},
    {"sku": "NV-5070",   "effective_month": "2026-05", "cost_multiplier": Decimal("1.20"), "supplier_code": "NVIDIA", "note": "NVIDIA 5 月二度上修 20%"},
    {"sku": "NV-5070TI", "effective_month": "2026-05", "cost_multiplier": Decimal("1.20"), "supplier_code": "NVIDIA", "note": "NVIDIA 5 月二度上修 20%"},
    {"sku": "NV-4080S",  "effective_month": "2026-05", "cost_multiplier": Decimal("1.20"), "supplier_code": "NVIDIA", "note": "NVIDIA 5 月二度上修 20%"},
    {"sku": "NV-4070S",  "effective_month": "2026-05", "cost_multiplier": Decimal("1.20"), "supplier_code": "NVIDIA", "note": "NVIDIA 5 月二度上修 20%"},
    # AI 熱潮：H100 漲價（2024-12 ~ 2025-Q3）然後 2025-Q4 回穩
    {"sku": "DC-H100-80",  "effective_month": "2024-12", "cost_multiplier": Decimal("1.25"), "supplier_code": "NVIDIA", "note": "AI 熱潮 NVIDIA H100 漲 25%"},
    {"sku": "DC-H100-SXM", "effective_month": "2024-12", "cost_multiplier": Decimal("1.25"), "supplier_code": "NVIDIA", "note": "AI 熱潮 NVIDIA H100 SXM 漲 25%"},
    {"sku": "DC-H100-80",  "effective_month": "2025-10", "cost_multiplier": Decimal("0.80"), "supplier_code": "NVIDIA", "note": "AI 熱回穩、NVIDIA H100 回原價"},
    {"sku": "DC-H100-SXM", "effective_month": "2025-10", "cost_multiplier": Decimal("0.80"), "supplier_code": "NVIDIA", "note": "AI 熱回穩、H100 SXM 回原價"},
    # RTX 4090 清庫存（2025-Q2）
    {"sku": "NV-4090", "effective_month": "2025-04", "cost_multiplier": Decimal("0.95"), "supplier_code": "NVIDIA", "note": "5090 上市後 4090 清庫存"},
    {"sku": "NV-4090", "effective_month": "2025-06", "cost_multiplier": Decimal("0.95"), "supplier_code": "NVIDIA", "note": "4090 持續清庫存"},
]


# ── Stockout windows ─────────────────────────────────────────────────
# In these months, PO `received` qty is severely cut for the SKU to
# create low_stock alerts / sales lost / aging stock.
class StockoutEvent(TypedDict):
    sku: str
    months: list[str]
    severity: Decimal          # 0.0=fully out, 1.0=normal
    note: str


STOCKOUT_EVENTS: Final[list[StockoutEvent]] = [
    {
        "sku": "NV-5070",
        "months": ["2025-09", "2026-02"],
        "severity": Decimal("0.10"),
        "note": "NVIDIA 端晶片 supply 緊",
    },
    {
        "sku": "NV-5070TI",
        "months": ["2025-09", "2026-02"],
        "severity": Decimal("0.10"),
        "note": "NVIDIA 端晶片 supply 緊",
    },
    {
        "sku": "NV-5090",
        "months": ["2025-01", "2025-02"],
        "severity": Decimal("0.25"),
        "note": "RTX 5090 上市初期供不應求",
    },
]


# ── Stock adjustment events ──────────────────────────────────────────
StockAdjustReason = Literal["damage", "count_loss", "count_gain", "sample", "other"]


class StockAdjustEvent(TypedDict):
    month: str
    sku: str
    quantity_delta: int          # negative=write-off / shortage, positive=found
    reason: StockAdjustReason
    note: str


STOCK_ADJUST_EVENTS: Final[list[StockAdjustEvent]] = [
    {"month": "2025-03", "sku": "WS-6000ADA",   "quantity_delta": -1, "reason": "damage",     "note": "高價工作站運輸損壞報廢"},
    {"month": "2025-08", "sku": "NV-4090",      "quantity_delta": -1, "reason": "damage",     "note": "RMA 後重新入庫但已損"},
    {"month": "2025-11", "sku": "NV-4080S",     "quantity_delta": -2, "reason": "count_loss", "note": "盤點短少 2 張"},
    {"month": "2026-01", "sku": "WS-4500ADA",   "quantity_delta": -1, "reason": "damage",     "note": "客退損傷無法銷售"},
    {"month": "2026-02", "sku": "NV-5060",      "quantity_delta":  1, "reason": "count_gain", "note": "盤盈 1 張"},
    {"month": "2026-04", "sku": "NV-4070",      "quantity_delta": -3, "reason": "damage",     "note": "倉儲水損 3 張"},
]


# ── Payment voids ────────────────────────────────────────────────────
class PaymentVoidEvent(TypedDict):
    kind: Literal["ar", "ap"]
    month: str
    party_code: str              # customer code (ar) or supplier code (ap)
    reason: str


PAYMENT_VOID_EVENTS: Final[list[PaymentVoidEvent]] = [
    {"kind": "ar", "month": "2025-09", "party_code": "BG_NUOQI",    "reason": "客戶退票、誤入帳已沖回"},
    {"kind": "ar", "month": "2026-02", "party_code": "BG_HAOXIANG", "reason": "誤入帳沖正"},
]


# ── Story summary for acceptance checks ──────────────────────────────
# Mirrors `project_seed_design.md` 10 條驗收條件 — Step 6 can read this
# to verify the generated dataset satisfies the demo contract.
ACCEPTANCE_KPIS: Final[list[str]] = [
    "每月月報都有資料、Q4 月份比 Q1 高 ≥ 25%",
    "2026-04/05 毛利率比 2026-01-03 平均低 ≥ 2 個百分點（大宇漲價效果）",
    "業務員 Top 3 vs Bottom 5 業績差距 ≥ 5 倍",
    "大同 RFM 555、祥豐 2026-05 跌到 R1FXMX 區段",
    "逾期 60+ 天 bucket ≥ 5 張未結清 AR",
    "≥ 5 SKU 在某些月份觸發 low_stock 警示",
    "≥ 6 筆盤點，含報廢 / 盤盈 / 盤虧各 ≥ 1",
    "≥ 2 筆 AR 收款作廢",
    "和欣毛利率明顯低於 VIP 平均",
    "慧林 / 慧達 學術毛利率最高",
]
