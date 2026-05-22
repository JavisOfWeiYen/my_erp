"""Supplier catalogue — 6 OEMs.

The company is modelled as a regional Taiwan distributor with first-party
authorisation from NVIDIA / AMD / Intel for silicon and Super Micro /
Dell / HPE for AI-server systems. Leadtek (an AIB) is intentionally
absent — that would put the user's employer on the supplier list and
also doesn't fit the "we sell *reference* parts and full servers"
positioning.

Each entry maps to the backend `SupplierCreate` payload (see
`backend/app/schemas/supplier.py`). The extra `code` field is for
cross-referencing from products.py / stories.py and is *not* sent to the
API.
"""
from __future__ import annotations

from typing import Final, TypedDict


class SupplierConfig(TypedDict):
    code: str  # internal cross-reference key only — never sent to API
    name: str
    contact_name: str | None
    phone: str | None
    email: str | None
    address: str | None
    tax_id: str | None
    payment_terms_days: int
    notes: str | None


SUPPLIERS: Final[list[SupplierConfig]] = [
    {
        "code": "NVIDIA",
        "name": "NVIDIA Corporation 台灣分公司",
        "contact_name": "Eric Chang / Channel Account Manager",
        "phone": "02-6605-3000",
        "email": "tw-channel@nvidia-fake.example.com",
        "address": "台北市信義區基隆路一段 333 號 24 樓",
        "tax_id": "27993301",
        "payment_terms_days": 30,
        "notes": "GeForce / RTX Ada / H100 / A100 / L40 / DGX；主力進貨來源、AI 熱潮漲價主角",
    },
    {
        "code": "AMD",
        "name": "AMD 超微半導體 台灣分公司",
        "contact_name": "Daphne Wu / Enterprise Channel",
        "phone": "02-2718-9929",
        "email": "tw-channel@amd-fake.example.com",
        "address": "台北市松山區敦化北路 167 號 8 樓",
        "tax_id": "16554871",
        "payment_terms_days": 45,
        "notes": "Radeon GPU / Instinct MI300 / EPYC CPU；MI300 出貨佔比偏低、demo 對照題材",
    },
    {
        "code": "INTEL",
        "name": "Intel Microelectronics 台灣分公司",
        "contact_name": "Steven Lin / Datacenter Sales",
        "phone": "02-8722-6000",
        "email": "tw-channel@intel-fake.example.com",
        "address": "台北市松山區民生東路三段 156 號 8 樓",
        "tax_id": "16554234",
        "payment_terms_days": 45,
        "notes": "Xeon CPU / Gaudi 3 AI 加速卡；Gaudi 出貨少、跟 MI300 一樣是 demo 對照題材",
    },
    {
        "code": "SMC",
        "name": "Super Micro Computer 美超微電腦股份有限公司",
        "contact_name": "Vincent Hsieh / AI Server Channel",
        "phone": "02-8226-3990",
        "email": "tw-channel@supermicro-fake.example.com",
        "address": "新北市中和區建一路 137 號",
        "tax_id": "23456771",
        "payment_terms_days": 60,
        "notes": "AI 整機伺服器（8×H100 / 8×H100 SXM）；單筆金額最大",
    },
    {
        "code": "DELL",
        "name": "Dell Technologies 台灣戴爾",
        "contact_name": "Karen Tsai / Enterprise Account",
        "phone": "0800-080-365",
        "email": "tw-enterprise@dell-fake.example.com",
        "address": "台北市內湖區堤頂大道二段 89 號 14 樓",
        "tax_id": "28556023",
        "payment_terms_days": 60,
        "notes": "PowerEdge XE9680 / R760xa AI 伺服器；含 Dell Financial Services 長帳期",
    },
    {
        "code": "HPE",
        "name": "HPE 慧與科技台灣股份有限公司",
        "contact_name": "Michael Kuo / Channel Sales",
        "phone": "02-3756-7777",
        "email": "tw-channel@hpe-fake.example.com",
        "address": "台北市信義區松仁路 97 號 12 樓",
        "tax_id": "70881455",
        "payment_terms_days": 60,
        "notes": "ProLiant DL380a Gen11 / Cray AI；量穩定",
    },
]


SUPPLIER_CODES: Final[set[str]] = {s["code"] for s in SUPPLIERS}

assert len(SUPPLIERS) == 6, f"expected 6 suppliers, got {len(SUPPLIERS)}"
assert len(SUPPLIER_CODES) == 6, "supplier codes must be unique"


def by_code(code: str) -> SupplierConfig:
    for s in SUPPLIERS:
        if s["code"] == code:
            return s
    raise KeyError(f"unknown supplier code: {code}")
