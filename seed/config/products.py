"""Product catalogue — 5 categories + 37 SKUs.

The company sells as a Taiwan regional OEM distributor:

- Silicon (NVIDIA / AMD / Intel) — GeForce / RTX Ada / H100 / A100 / L40
  / Instinct MI300X / Gaudi 3
- AI servers (Super Micro / Dell / HPE / NVIDIA DGX) — high-ticket
  full systems, low volume but dominate revenue per unit

Each entry maps to the backend `ProductCreate` payload (see
`backend/app/schemas/product.py`), with these seed-only side-channels:

- `category_code`  : resolved against CATEGORIES at insert time
- `launch_month`   : "YYYY-MM" — Step 4 timeline only starts trading
                     this SKU after this month
- `supplier_codes` : list of supplier codes that can supply this SKU;
                     the first entry is the *default* PO target, the
                     rest are fallbacks. Codes must exist in
                     suppliers.py.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Final, TypedDict


class CategoryConfig(TypedDict):
    code: str
    name: str
    description: str | None


class ProductConfig(TypedDict):
    sku: str
    name: str
    category_code: str
    unit: str
    unit_price: Decimal
    cost_price: Decimal
    low_stock_threshold: int
    launch_month: str
    supplier_codes: list[str]
    description: str | None


CATEGORIES: Final[list[CategoryConfig]] = [
    {
        "code": "GPU_CONSUMER_NV",
        "name": "消費級遊戲卡 - NVIDIA",
        "description": "NVIDIA GeForce RTX 40 / 50 系列消費級顯示卡",
    },
    {
        "code": "GPU_CONSUMER_AMD",
        "name": "消費級遊戲卡 - AMD",
        "description": "AMD Radeon RX 7000 系列消費級顯示卡",
    },
    {
        "code": "GPU_WORKSTATION",
        "name": "工作站顯示卡",
        "description": "NVIDIA RTX Ada 系列工作站專業卡",
    },
    {
        "code": "GPU_DATACENTER",
        "name": "資料中心 / AI 加速卡",
        "description": "NVIDIA H100/A100/L40、AMD Instinct、Intel Gaudi AI 加速卡",
    },
    {
        "code": "AI_SERVER",
        "name": "AI 伺服器整機",
        "description": "Super Micro / Dell / HPE / NVIDIA DGX 整合式 AI 伺服器",
    },
]


def _d(value: str | int) -> Decimal:
    return Decimal(str(value))


PRODUCTS: Final[list[ProductConfig]] = [
    # ── 類別 1：消費級遊戲卡 (NVIDIA GeForce) — 12 SKU ───────────────────
    {
        "sku": "NV-5090",
        "name": "NVIDIA GeForce RTX 5090 32GB",
        "category_code": "GPU_CONSUMER_NV",
        "unit": "張",
        "unit_price": _d(82000),
        "cost_price": _d(68000),
        "low_stock_threshold": 5,
        "launch_month": "2025-01",
        "supplier_codes": ["NVIDIA"],
        "description": "旗艦級顯示卡，2025 年 1 月上市，初期供不應求",
    },
    {
        "sku": "NV-5080",
        "name": "NVIDIA GeForce RTX 5080 16GB",
        "category_code": "GPU_CONSUMER_NV",
        "unit": "張",
        "unit_price": _d(42000),
        "cost_price": _d(35500),
        "low_stock_threshold": 8,
        "launch_month": "2025-01",
        "supplier_codes": ["NVIDIA"],
        "description": "RTX 50 系列次旗艦",
    },
    {
        "sku": "NV-5070TI",
        "name": "NVIDIA GeForce RTX 5070 Ti 16GB",
        "category_code": "GPU_CONSUMER_NV",
        "unit": "張",
        "unit_price": _d(28500),
        "cost_price": _d(23800),
        "low_stock_threshold": 12,
        "launch_month": "2025-02",
        "supplier_codes": ["NVIDIA"],
        "description": "RTX 50 主流熱銷型號（2026-04/05 NVIDIA 區域配額調整漲價影響 SKU）",
    },
    {
        "sku": "NV-5070",
        "name": "NVIDIA GeForce RTX 5070 12GB",
        "category_code": "GPU_CONSUMER_NV",
        "unit": "張",
        "unit_price": _d(19800),
        "cost_price": _d(16500),
        "low_stock_threshold": 15,
        "launch_month": "2025-03",
        "supplier_codes": ["NVIDIA"],
        "description": "RTX 50 主流甜蜜點（漲價 + 2025/2026 缺貨主角）",
    },
    {
        "sku": "NV-5060TI",
        "name": "NVIDIA GeForce RTX 5060 Ti 16GB",
        "category_code": "GPU_CONSUMER_NV",
        "unit": "張",
        "unit_price": _d(14800),
        "cost_price": _d(12300),
        "low_stock_threshold": 12,
        "launch_month": "2025-04",
        "supplier_codes": ["NVIDIA"],
        "description": "RTX 50 中階",
    },
    {
        "sku": "NV-5060",
        "name": "NVIDIA GeForce RTX 5060 8GB",
        "category_code": "GPU_CONSUMER_NV",
        "unit": "張",
        "unit_price": _d(11500),
        "cost_price": _d(9500),
        "low_stock_threshold": 15,
        "launch_month": "2025-05",
        "supplier_codes": ["NVIDIA"],
        "description": "RTX 50 入門",
    },
    {
        "sku": "NV-4090",
        "name": "NVIDIA GeForce RTX 4090 24GB",
        "category_code": "GPU_CONSUMER_NV",
        "unit": "張",
        "unit_price": _d(68000),
        "cost_price": _d(58000),
        "low_stock_threshold": 5,
        "launch_month": "2024-12",
        "supplier_codes": ["NVIDIA"],
        "description": "RTX 40 前旗艦；5090 上市後降價清庫存",
    },
    {
        "sku": "NV-4080S",
        "name": "NVIDIA GeForce RTX 4080 SUPER 16GB",
        "category_code": "GPU_CONSUMER_NV",
        "unit": "張",
        "unit_price": _d(38500),
        "cost_price": _d(32500),
        "low_stock_threshold": 8,
        "launch_month": "2024-12",
        "supplier_codes": ["NVIDIA"],
        "description": "RTX 40 中高階（2026-04/05 漲價影響 SKU）",
    },
    {
        "sku": "NV-4070S",
        "name": "NVIDIA GeForce RTX 4070 SUPER 12GB",
        "category_code": "GPU_CONSUMER_NV",
        "unit": "張",
        "unit_price": _d(22500),
        "cost_price": _d(18800),
        "low_stock_threshold": 12,
        "launch_month": "2024-12",
        "supplier_codes": ["NVIDIA"],
        "description": "RTX 40 主流（2026-04/05 漲價影響 SKU）",
    },
    {
        "sku": "NV-4070",
        "name": "NVIDIA GeForce RTX 4070 12GB",
        "category_code": "GPU_CONSUMER_NV",
        "unit": "張",
        "unit_price": _d(19500),
        "cost_price": _d(16200),
        "low_stock_threshold": 12,
        "launch_month": "2024-12",
        "supplier_codes": ["NVIDIA"],
        "description": "RTX 40 主流",
    },
    {
        "sku": "NV-4060TI",
        "name": "NVIDIA GeForce RTX 4060 Ti 8GB",
        "category_code": "GPU_CONSUMER_NV",
        "unit": "張",
        "unit_price": _d(13500),
        "cost_price": _d(11200),
        "low_stock_threshold": 12,
        "launch_month": "2024-12",
        "supplier_codes": ["NVIDIA"],
        "description": "RTX 40 中階",
    },
    {
        "sku": "NV-4060",
        "name": "NVIDIA GeForce RTX 4060 8GB",
        "category_code": "GPU_CONSUMER_NV",
        "unit": "張",
        "unit_price": _d(10500),
        "cost_price": _d(8700),
        "low_stock_threshold": 15,
        "launch_month": "2024-12",
        "supplier_codes": ["NVIDIA"],
        "description": "RTX 40 入門",
    },
    # ── 類別 2：消費級遊戲卡 (AMD Radeon) — 5 SKU ────────────────────────
    {
        "sku": "AMD-7900XTX",
        "name": "AMD Radeon RX 7900 XTX 24GB",
        "category_code": "GPU_CONSUMER_AMD",
        "unit": "張",
        "unit_price": _d(26500),
        "cost_price": _d(22000),
        "low_stock_threshold": 6,
        "launch_month": "2024-12",
        "supplier_codes": ["AMD"],
        "description": "AMD 旗艦",
    },
    {
        "sku": "AMD-7900XT",
        "name": "AMD Radeon RX 7900 XT 20GB",
        "category_code": "GPU_CONSUMER_AMD",
        "unit": "張",
        "unit_price": _d(21500),
        "cost_price": _d(17800),
        "low_stock_threshold": 8,
        "launch_month": "2024-12",
        "supplier_codes": ["AMD"],
        "description": "AMD 次旗艦",
    },
    {
        "sku": "AMD-7800XT",
        "name": "AMD Radeon RX 7800 XT 16GB",
        "category_code": "GPU_CONSUMER_AMD",
        "unit": "張",
        "unit_price": _d(17500),
        "cost_price": _d(14500),
        "low_stock_threshold": 10,
        "launch_month": "2024-12",
        "supplier_codes": ["AMD"],
        "description": "AMD 中高階",
    },
    {
        "sku": "AMD-7700XT",
        "name": "AMD Radeon RX 7700 XT 12GB",
        "category_code": "GPU_CONSUMER_AMD",
        "unit": "張",
        "unit_price": _d(14500),
        "cost_price": _d(12000),
        "low_stock_threshold": 10,
        "launch_month": "2024-12",
        "supplier_codes": ["AMD"],
        "description": "AMD 中階",
    },
    {
        "sku": "AMD-7600XT",
        "name": "AMD Radeon RX 7600 XT 16GB",
        "category_code": "GPU_CONSUMER_AMD",
        "unit": "張",
        "unit_price": _d(11800),
        "cost_price": _d(9800),
        "low_stock_threshold": 12,
        "launch_month": "2024-12",
        "supplier_codes": ["AMD"],
        "description": "AMD 入門",
    },
    # ── 類別 3：工作站專業卡 (NVIDIA RTX Ada) — 6 SKU ────────────────────
    {
        "sku": "WS-6000ADA",
        "name": "NVIDIA RTX 6000 Ada 48GB",
        "category_code": "GPU_WORKSTATION",
        "unit": "張",
        "unit_price": _d(265000),
        "cost_price": _d(225000),
        "low_stock_threshold": 2,
        "launch_month": "2024-12",
        "supplier_codes": ["NVIDIA"],
        "description": "頂級渲染 / AI 工作站卡",
    },
    {
        "sku": "WS-5880ADA",
        "name": "NVIDIA RTX 5880 Ada 48GB",
        "category_code": "GPU_WORKSTATION",
        "unit": "張",
        "unit_price": _d(200000),
        "cost_price": _d(168000),
        "low_stock_threshold": 2,
        "launch_month": "2024-12",
        "supplier_codes": ["NVIDIA"],
        "description": "高階工作站卡",
    },
    {
        "sku": "WS-5000ADA",
        "name": "NVIDIA RTX 5000 Ada 32GB",
        "category_code": "GPU_WORKSTATION",
        "unit": "張",
        "unit_price": _d(138000),
        "cost_price": _d(115000),
        "low_stock_threshold": 3,
        "launch_month": "2024-12",
        "supplier_codes": ["NVIDIA"],
        "description": "中高階工作站",
    },
    {
        "sku": "WS-4500ADA",
        "name": "NVIDIA RTX 4500 Ada 24GB",
        "category_code": "GPU_WORKSTATION",
        "unit": "張",
        "unit_price": _d(85000),
        "cost_price": _d(71000),
        "low_stock_threshold": 4,
        "launch_month": "2024-12",
        "supplier_codes": ["NVIDIA"],
        "description": "中階工作站",
    },
    {
        "sku": "WS-4000ADA",
        "name": "NVIDIA RTX 4000 Ada 20GB",
        "category_code": "GPU_WORKSTATION",
        "unit": "張",
        "unit_price": _d(45000),
        "cost_price": _d(37500),
        "low_stock_threshold": 5,
        "launch_month": "2024-12",
        "supplier_codes": ["NVIDIA"],
        "description": "主流工作站",
    },
    {
        "sku": "WS-2000ADA",
        "name": "NVIDIA RTX 2000 Ada 16GB",
        "category_code": "GPU_WORKSTATION",
        "unit": "張",
        "unit_price": _d(22000),
        "cost_price": _d(18200),
        "low_stock_threshold": 6,
        "launch_month": "2024-12",
        "supplier_codes": ["NVIDIA"],
        "description": "入門工作站",
    },
    # ── 類別 4：資料中心 / AI 加速卡 — 8 SKU（6 NVIDIA + 1 AMD + 1 Intel）──
    {
        "sku": "DC-H100-80",
        "name": "NVIDIA H100 80GB PCIe",
        "category_code": "GPU_DATACENTER",
        "unit": "張",
        "unit_price": _d(980000),
        "cost_price": _d(840000),
        "low_stock_threshold": 2,
        "launch_month": "2024-12",
        "supplier_codes": ["NVIDIA"],
        "description": "AI 熱潮主角（2024-12 ~ 2025-Q3 漲價）",
    },
    {
        "sku": "DC-H100-SXM",
        "name": "NVIDIA H100 SXM5 80GB",
        "category_code": "GPU_DATACENTER",
        "unit": "張",
        "unit_price": _d(1180000),
        "cost_price": _d(1020000),
        "low_stock_threshold": 2,
        "launch_month": "2024-12",
        "supplier_codes": ["NVIDIA"],
        "description": "AI 高階；SXM 介面整機板",
    },
    {
        "sku": "DC-A100-80",
        "name": "NVIDIA A100 80GB PCIe",
        "category_code": "GPU_DATACENTER",
        "unit": "張",
        "unit_price": _d(580000),
        "cost_price": _d(485000),
        "low_stock_threshold": 2,
        "launch_month": "2024-12",
        "supplier_codes": ["NVIDIA"],
        "description": "前世代 AI 卡仍熱賣",
    },
    {
        "sku": "DC-L40S",
        "name": "NVIDIA L40S 48GB",
        "category_code": "GPU_DATACENTER",
        "unit": "張",
        "unit_price": _d(320000),
        "cost_price": _d(268000),
        "low_stock_threshold": 3,
        "launch_month": "2024-12",
        "supplier_codes": ["NVIDIA"],
        "description": "AI + 視覺化通用卡",
    },
    {
        "sku": "DC-L40",
        "name": "NVIDIA L40 48GB",
        "category_code": "GPU_DATACENTER",
        "unit": "張",
        "unit_price": _d(280000),
        "cost_price": _d(235000),
        "low_stock_threshold": 3,
        "launch_month": "2024-12",
        "supplier_codes": ["NVIDIA"],
        "description": "視覺化 / 推論",
    },
    {
        "sku": "DC-L4",
        "name": "NVIDIA L4 24GB",
        "category_code": "GPU_DATACENTER",
        "unit": "張",
        "unit_price": _d(88000),
        "cost_price": _d(73000),
        "low_stock_threshold": 4,
        "launch_month": "2024-12",
        "supplier_codes": ["NVIDIA"],
        "description": "低功耗推論卡",
    },
    {
        "sku": "DC-MI300X",
        "name": "AMD Instinct MI300X 192GB",
        "category_code": "GPU_DATACENTER",
        "unit": "張",
        "unit_price": _d(720000),
        "cost_price": _d(610000),
        "low_stock_threshold": 2,
        "launch_month": "2024-12",
        "supplier_codes": ["AMD"],
        "description": "AMD 對標 H100 / H200；demo「為什麼出貨佔比低」題材",
    },
    {
        "sku": "DC-GAUDI3",
        "name": "Intel Gaudi 3 96GB OAM",
        "category_code": "GPU_DATACENTER",
        "unit": "張",
        "unit_price": _d(480000),
        "cost_price": _d(400000),
        "low_stock_threshold": 2,
        "launch_month": "2025-04",
        "supplier_codes": ["INTEL"],
        "description": "Intel AI 加速卡；2025-Q2 上市；CP 值高但生態系新、demo 對照題材",
    },
    # ── 類別 5：AI 伺服器整機 — 6 SKU ────────────────────────────────────
    {
        "sku": "SVR-SMC-8H100",
        "name": "Super Micro AS-2125GS-TNHR 8×H100 PCIe AI 伺服器",
        "category_code": "AI_SERVER",
        "unit": "台",
        "unit_price": _d(8500000),
        "cost_price": _d(7200000),
        "low_stock_threshold": 1,
        "launch_month": "2024-12",
        "supplier_codes": ["SMC"],
        "description": "2U 8×H100 PCIe；雲端 / AI 公司主力導入機型",
    },
    {
        "sku": "SVR-SMC-8H100SXM",
        "name": "Super Micro SYS-821GE-TNHR 8×H100 SXM5 AI 伺服器",
        "category_code": "AI_SERVER",
        "unit": "台",
        "unit_price": _d(11500000),
        "cost_price": _d(9800000),
        "low_stock_threshold": 1,
        "launch_month": "2024-12",
        "supplier_codes": ["SMC"],
        "description": "8U HGX H100 SXM5 平台；高階 AI 訓練",
    },
    {
        "sku": "SVR-DELL-XE9680",
        "name": "Dell PowerEdge XE9680 8×H100 SXM5 AI 伺服器",
        "category_code": "AI_SERVER",
        "unit": "台",
        "unit_price": _d(12800000),
        "cost_price": _d(10900000),
        "low_stock_threshold": 1,
        "launch_month": "2024-12",
        "supplier_codes": ["DELL"],
        "description": "Dell 旗艦 AI 訓練機；含 Dell Financial Services",
    },
    {
        "sku": "SVR-DELL-R760XA",
        "name": "Dell PowerEdge R760xa 4×L40S 推論伺服器",
        "category_code": "AI_SERVER",
        "unit": "台",
        "unit_price": _d(2200000),
        "cost_price": _d(1850000),
        "low_stock_threshold": 1,
        "launch_month": "2024-12",
        "supplier_codes": ["DELL"],
        "description": "2U 4×L40S；推論 / 邊緣 AI",
    },
    {
        "sku": "SVR-HPE-DL380A",
        "name": "HPE ProLiant DL380a Gen11 4×L40S 伺服器",
        "category_code": "AI_SERVER",
        "unit": "台",
        "unit_price": _d(1950000),
        "cost_price": _d(1650000),
        "low_stock_threshold": 1,
        "launch_month": "2024-12",
        "supplier_codes": ["HPE"],
        "description": "HPE 主流 AI 推論平台",
    },
    {
        "sku": "SVR-NV-DGX-H100",
        "name": "NVIDIA DGX H100 8×H100 整合式 AI 系統",
        "category_code": "AI_SERVER",
        "unit": "台",
        "unit_price": _d(15500000),
        "cost_price": _d(13200000),
        "low_stock_threshold": 1,
        "launch_month": "2024-12",
        "supplier_codes": ["NVIDIA"],
        "description": "NVIDIA 原廠整合 DGX；含 InfiniBand + NVMe + 軟體棧",
    },
]


PRODUCT_SKUS: Final[set[str]] = {p["sku"] for p in PRODUCTS}
CATEGORY_CODES: Final[set[str]] = {c["code"] for c in CATEGORIES}

assert len(PRODUCTS) == 37, f"expected 37 SKUs, got {len(PRODUCTS)}"
assert len(PRODUCT_SKUS) == 37, "SKUs must be unique"
assert len(CATEGORIES) == 5, f"expected 5 categories, got {len(CATEGORIES)}"
assert len(CATEGORY_CODES) == 5, "category codes must be unique"
assert all(p["category_code"] in CATEGORY_CODES for p in PRODUCTS), "category_code must match"


def by_sku(sku: str) -> ProductConfig:
    for p in PRODUCTS:
        if p["sku"] == sku:
            return p
    raise KeyError(f"unknown SKU: {sku}")


def by_category(code: str) -> list[ProductConfig]:
    return [p for p in PRODUCTS if p["category_code"] == code]
