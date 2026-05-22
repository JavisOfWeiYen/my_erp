"""Personnel catalogue — 50 staff (admin 2 + manager 6 + sales 28 + warehouse 14).

Each entry is consumed twice during seed:

1. `POST /users` — `username`, `password`, `email`, `full_name`, `role_name`.
2. `POST /employees` — `department`, `title`, `hire_date`, `employment_type`,
   `initial_salary` (the API auto-creates the first salary_record with
   reason='hire').

Extra seed-only fields:

- `code`            : internal cross-reference, never sent to the API.
- `tier`            : only for sales — drives Step 4's weighted assignment
                      ("star" / "mid" / "average" / "declining" / "newbie").
- `notes`           : copied into the employee record `notes`.

PLAN.html section H pins three "明星" + three "衰退" + one "新人崛起" to
specific names so analytics demos can reference them. The remaining 21
sales are anonymous "中段" / "一般" archetypes.

Password for every seeded account is `Demo!2026`. The seed must NOT touch
INITIAL_ADMIN_* — `demo_admin` here is an entirely separate account.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Final, Literal, TypedDict


DEFAULT_PASSWORD: Final[str] = "Demo!2026"

RoleName = Literal["admin", "manager", "sales", "warehouse"]
Department = Literal["sales", "warehouse", "accounting", "management", "it"]
EmploymentType = Literal["full_time", "part_time", "contractor"]
SalesTier = Literal["star", "mid", "average", "declining", "newbie"]


class PersonConfig(TypedDict, total=False):
    code: str
    username: str
    full_name: str
    email: str
    role_name: RoleName
    department: Department
    title: str
    hire_date: date
    employment_type: EmploymentType
    initial_salary: Decimal
    tier: SalesTier  # sales only
    notes: str | None


def _d(value: int | str) -> Decimal:
    return Decimal(str(value))


def _email(username: str) -> str:
    return f"{username}@my-erp-demo.example.com.tw"


# ── Admin (2) ─────────────────────────────────────────────────────────
ADMINS: Final[list[PersonConfig]] = [
    {
        "code": "ADM_DEMO_ADMIN",
        "username": "demo_admin",
        "full_name": "Demo 系統管理員",
        "email": _email("demo_admin"),
        "role_name": "admin",
        "department": "it",
        "title": "Demo 系統管理員",
        "hire_date": date(2023, 1, 16),
        "employment_type": "full_time",
        "initial_salary": _d(65000),
        "notes": "seed 用 demo admin，跟 INITIAL_ADMIN 隔離",
    },
    {
        "code": "ADM_IT_LEAD",
        "username": "it_lead",
        "full_name": "周冠廷",
        "email": _email("it_lead"),
        "role_name": "admin",
        "department": "it",
        "title": "IT 部門主管",
        "hire_date": date(2022, 8, 15),
        "employment_type": "full_time",
        "initial_salary": _d(82000),
        "notes": None,
    },
]

# ── Manager (6) ───────────────────────────────────────────────────────
MANAGERS: Final[list[PersonConfig]] = [
    {
        "code": "MGR_CEO",
        "username": "ceo_chiu",
        "full_name": "邱建宏",
        "email": _email("ceo_chiu"),
        "role_name": "manager",
        "department": "management",
        "title": "總經理",
        "hire_date": date(2022, 6, 1),
        "employment_type": "full_time",
        "initial_salary": _d(180000),
        "notes": None,
    },
    {
        "code": "MGR_SALES_VP",
        "username": "sales_vp",
        "full_name": "楊立群",
        "email": _email("sales_vp"),
        "role_name": "manager",
        "department": "sales",
        "title": "業務副總",
        "hire_date": date(2022, 7, 4),
        "employment_type": "full_time",
        "initial_salary": _d(135000),
        "notes": None,
    },
    {
        "code": "MGR_SALES_DIR",
        "username": "sales_dir",
        "full_name": "鄭文豪",
        "email": _email("sales_dir"),
        "role_name": "manager",
        "department": "sales",
        "title": "業務經理",
        "hire_date": date(2023, 3, 13),
        "employment_type": "full_time",
        "initial_salary": _d(95000),
        "notes": None,
    },
    {
        "code": "MGR_FINANCE",
        "username": "finance_mgr",
        "full_name": "許麗芬",
        "email": _email("finance_mgr"),
        "role_name": "manager",
        "department": "accounting",
        "title": "財務主管",
        "hire_date": date(2022, 11, 7),
        "employment_type": "full_time",
        "initial_salary": _d(92000),
        "notes": None,
    },
    {
        "code": "MGR_PURCHASE",
        "username": "purchase_mgr",
        "full_name": "曾建宏",
        "email": _email("purchase_mgr"),
        "role_name": "manager",
        "department": "management",
        "title": "採購主管",
        "hire_date": date(2023, 1, 9),
        "employment_type": "full_time",
        "initial_salary": _d(90000),
        "notes": None,
    },
    {
        "code": "MGR_OPS",
        "username": "ops_mgr",
        "full_name": "廖怡君",
        "email": _email("ops_mgr"),
        "role_name": "manager",
        "department": "management",
        "title": "營運主管",
        "hire_date": date(2023, 5, 22),
        "employment_type": "full_time",
        "initial_salary": _d(88000),
        "notes": None,
    },
]

# ── Sales (28) ────────────────────────────────────────────────────────
# PLAN.html section H pins these 7 to scripted roles (3 star + 3 declining + 1 newbie):
#   STAR_1 張俊宏 / STAR_2 李曉雯 / STAR_3 王智浩
#   DECLINE_1 黃秀美 / DECLINE_2 吳建華 / DECLINE_3 劉雅婷
#   NEWBIE 蔡明軒
SALES: Final[list[PersonConfig]] = [
    # — Stars (3) —
    {
        "code": "SLS_STAR_1",
        "username": "zhang_junhong",
        "full_name": "張俊宏",
        "email": _email("zhang_junhong"),
        "role_name": "sales",
        "department": "sales",
        "title": "資深業務代表",
        "hire_date": date(2022, 9, 1),
        "employment_type": "full_time",
        "initial_salary": _d(95000),
        "tier": "star",
        "notes": "明星 #1；主接大同雲端 / 立通科技",
    },
    {
        "code": "SLS_STAR_2",
        "username": "li_xiaowen",
        "full_name": "李曉雯",
        "email": _email("li_xiaowen"),
        "role_name": "sales",
        "department": "sales",
        "title": "資深業務代表",
        "hire_date": date(2022, 10, 17),
        "employment_type": "full_time",
        "initial_salary": _d(90000),
        "tier": "star",
        "notes": "明星 #2；主攻工作站 / 學術；2025-08~09 病假",
    },
    {
        "code": "SLS_STAR_3",
        "username": "wang_zhihao",
        "full_name": "王智浩",
        "email": _email("wang_zhihao"),
        "role_name": "sales",
        "department": "sales",
        "title": "資深業務代表",
        "hire_date": date(2023, 2, 6),
        "employment_type": "full_time",
        "initial_salary": _d(88000),
        "tier": "star",
        "notes": "明星 #3；電競通路；負責祥豐電腦",
    },
    # — Mid (12) —
    {
        "code": "SLS_MID_01",
        "username": "chen_yijun",
        "full_name": "陳怡君",
        "email": _email("chen_yijun"),
        "role_name": "sales",
        "department": "sales",
        "title": "業務代表",
        "hire_date": date(2023, 5, 22),
        "employment_type": "full_time",
        "initial_salary": _d(62000),
        "tier": "mid",
        "notes": None,
    },
    {
        "code": "SLS_MID_02",
        "username": "lin_meiling",
        "full_name": "林美玲",
        "email": _email("lin_meiling"),
        "role_name": "sales",
        "department": "sales",
        "title": "業務代表",
        "hire_date": date(2023, 7, 3),
        "employment_type": "full_time",
        "initial_salary": _d(60000),
        "tier": "mid",
        "notes": None,
    },
    {
        "code": "SLS_MID_03",
        "username": "huang_zhihui",
        "full_name": "黃志輝",
        "email": _email("huang_zhihui"),
        "role_name": "sales",
        "department": "sales",
        "title": "業務代表",
        "hire_date": date(2023, 8, 15),
        "employment_type": "full_time",
        "initial_salary": _d(63000),
        "tier": "mid",
        "notes": None,
    },
    {
        "code": "SLS_MID_04",
        "username": "wu_bingyang",
        "full_name": "吳秉洋",
        "email": _email("wu_bingyang"),
        "role_name": "sales",
        "department": "sales",
        "title": "業務代表",
        "hire_date": date(2023, 9, 18),
        "employment_type": "full_time",
        "initial_salary": _d(58000),
        "tier": "mid",
        "notes": None,
    },
    {
        "code": "SLS_MID_05",
        "username": "liu_xinyi",
        "full_name": "劉欣怡",
        "email": _email("liu_xinyi"),
        "role_name": "sales",
        "department": "sales",
        "title": "業務代表",
        "hire_date": date(2023, 11, 7),
        "employment_type": "full_time",
        "initial_salary": _d(56000),
        "tier": "mid",
        "notes": None,
    },
    {
        "code": "SLS_MID_06",
        "username": "cai_zheming",
        "full_name": "蔡哲銘",
        "email": _email("cai_zheming"),
        "role_name": "sales",
        "department": "sales",
        "title": "業務代表",
        "hire_date": date(2024, 1, 8),
        "employment_type": "full_time",
        "initial_salary": _d(60000),
        "tier": "mid",
        "notes": None,
    },
    {
        "code": "SLS_MID_07",
        "username": "zheng_yawen",
        "full_name": "鄭雅雯",
        "email": _email("zheng_yawen"),
        "role_name": "sales",
        "department": "sales",
        "title": "業務代表",
        "hire_date": date(2024, 2, 19),
        "employment_type": "full_time",
        "initial_salary": _d(64000),
        "tier": "mid",
        "notes": None,
    },
    {
        "code": "SLS_MID_08",
        "username": "xie_jiawei",
        "full_name": "謝家瑋",
        "email": _email("xie_jiawei"),
        "role_name": "sales",
        "department": "sales",
        "title": "業務代表",
        "hire_date": date(2024, 3, 11),
        "employment_type": "full_time",
        "initial_salary": _d(57000),
        "tier": "mid",
        "notes": None,
    },
    {
        "code": "SLS_MID_09",
        "username": "hong_xiumin",
        "full_name": "洪秀敏",
        "email": _email("hong_xiumin"),
        "role_name": "sales",
        "department": "sales",
        "title": "業務代表",
        "hire_date": date(2024, 4, 22),
        "employment_type": "full_time",
        "initial_salary": _d(59000),
        "tier": "mid",
        "notes": None,
    },
    {
        "code": "SLS_MID_10",
        "username": "guo_chengyi",
        "full_name": "郭承毅",
        "email": _email("guo_chengyi"),
        "role_name": "sales",
        "department": "sales",
        "title": "業務代表",
        "hire_date": date(2024, 6, 3),
        "employment_type": "full_time",
        "initial_salary": _d(55000),
        "tier": "mid",
        "notes": None,
    },
    {
        "code": "SLS_MID_11",
        "username": "qiu_minghao",
        "full_name": "邱明浩",
        "email": _email("qiu_minghao"),
        "role_name": "sales",
        "department": "sales",
        "title": "業務代表",
        "hire_date": date(2024, 7, 15),
        "employment_type": "full_time",
        "initial_salary": _d(58000),
        "tier": "mid",
        "notes": None,
    },
    {
        "code": "SLS_MID_12",
        "username": "zeng_peiling",
        "full_name": "曾佩玲",
        "email": _email("zeng_peiling"),
        "role_name": "sales",
        "department": "sales",
        "title": "業務代表",
        "hire_date": date(2024, 9, 9),
        "employment_type": "full_time",
        "initial_salary": _d(56000),
        "tier": "mid",
        "notes": None,
    },
    # — Average (9) —
    {
        "code": "SLS_AVG_01",
        "username": "liao_jincheng",
        "full_name": "廖晉誠",
        "email": _email("liao_jincheng"),
        "role_name": "sales",
        "department": "sales",
        "title": "業務專員",
        "hire_date": date(2024, 5, 6),
        "employment_type": "full_time",
        "initial_salary": _d(50000),
        "tier": "average",
        "notes": None,
    },
    {
        "code": "SLS_AVG_02",
        "username": "lai_yiping",
        "full_name": "賴依屏",
        "email": _email("lai_yiping"),
        "role_name": "sales",
        "department": "sales",
        "title": "業務專員",
        "hire_date": date(2024, 8, 19),
        "employment_type": "full_time",
        "initial_salary": _d(48000),
        "tier": "average",
        "notes": None,
    },
    {
        "code": "SLS_AVG_03",
        "username": "xu_kaihong",
        "full_name": "徐凱鴻",
        "email": _email("xu_kaihong"),
        "role_name": "sales",
        "department": "sales",
        "title": "業務專員",
        "hire_date": date(2024, 10, 14),
        "employment_type": "full_time",
        "initial_salary": _d(47000),
        "tier": "average",
        "notes": None,
    },
    {
        "code": "SLS_AVG_04",
        "username": "lin_zhicheng",
        "full_name": "林志成",
        "email": _email("lin_zhicheng"),
        "role_name": "sales",
        "department": "sales",
        "title": "業務專員",
        "hire_date": date(2024, 11, 25),
        "employment_type": "full_time",
        "initial_salary": _d(46000),
        "tier": "average",
        "notes": "主做散戶與小通路",
    },
    {
        "code": "SLS_AVG_05",
        "username": "jiang_yili",
        "full_name": "江依俐",
        "email": _email("jiang_yili"),
        "role_name": "sales",
        "department": "sales",
        "title": "業務專員",
        "hire_date": date(2025, 1, 13),
        "employment_type": "full_time",
        "initial_salary": _d(45000),
        "tier": "average",
        "notes": None,
    },
    {
        "code": "SLS_AVG_06",
        "username": "ye_qiuxian",
        "full_name": "葉秋賢",
        "email": _email("ye_qiuxian"),
        "role_name": "sales",
        "department": "sales",
        "title": "業務專員",
        "hire_date": date(2025, 2, 18),
        "employment_type": "full_time",
        "initial_salary": _d(48000),
        "tier": "average",
        "notes": None,
    },
    {
        "code": "SLS_AVG_07",
        "username": "pan_yixiang",
        "full_name": "潘奕翔",
        "email": _email("pan_yixiang"),
        "role_name": "sales",
        "department": "sales",
        "title": "業務專員",
        "hire_date": date(2025, 4, 7),
        "employment_type": "full_time",
        "initial_salary": _d(45000),
        "tier": "average",
        "notes": "主做散戶",
    },
    {
        "code": "SLS_AVG_08",
        "username": "yu_huizhen",
        "full_name": "余惠真",
        "email": _email("yu_huizhen"),
        "role_name": "sales",
        "department": "sales",
        "title": "業務專員",
        "hire_date": date(2025, 5, 19),
        "employment_type": "full_time",
        "initial_salary": _d(46000),
        "tier": "average",
        "notes": None,
    },
    {
        "code": "SLS_AVG_09",
        "username": "yan_chengjie",
        "full_name": "顏承杰",
        "email": _email("yan_chengjie"),
        "role_name": "sales",
        "department": "sales",
        "title": "業務專員",
        "hire_date": date(2025, 7, 22),
        "employment_type": "full_time",
        "initial_salary": _d(45000),
        "tier": "average",
        "notes": None,
    },
    # — Declining (3) —
    {
        "code": "SLS_DECLINE_1",
        "username": "huang_xiumei",
        "full_name": "黃秀美",
        "email": _email("huang_xiumei"),
        "role_name": "sales",
        "department": "sales",
        "title": "資深業務代表",
        "hire_date": date(2022, 12, 12),
        "employment_type": "full_time",
        "initial_salary": _d(75000),
        "tier": "declining",
        "notes": "衰退 #1；2025-Q3 後業績逐月下滑",
    },
    {
        "code": "SLS_DECLINE_2",
        "username": "wu_jianhua",
        "full_name": "吳建華",
        "email": _email("wu_jianhua"),
        "role_name": "sales",
        "department": "sales",
        "title": "業務代表",
        "hire_date": date(2023, 6, 1),
        "employment_type": "full_time",
        "initial_salary": _d(68000),
        "tier": "declining",
        "notes": "衰退 #2；2026-Q1 後跟和欣衝突、丟掉客戶",
    },
    {
        "code": "SLS_DECLINE_3",
        "username": "liu_yating",
        "full_name": "劉雅婷",
        "email": _email("liu_yating"),
        "role_name": "sales",
        "department": "sales",
        "title": "業務代表",
        "hire_date": date(2023, 10, 20),
        "employment_type": "full_time",
        "initial_salary": _d(58000),
        "tier": "declining",
        "notes": "衰退 #3；2026-04 完全沒開單（疑似離職前夕）",
    },
    # — Newbie rising (1) —
    {
        "code": "SLS_NEWBIE",
        "username": "cai_mingxuan",
        "full_name": "蔡明軒",
        "email": _email("cai_mingxuan"),
        "role_name": "sales",
        "department": "sales",
        "title": "業務專員",
        "hire_date": date(2026, 1, 15),
        "employment_type": "full_time",
        "initial_salary": _d(42000),
        "tier": "newbie",
        "notes": "2026-01 入職；2026-04/05 爆發",
    },
]

# ── Warehouse (14) ────────────────────────────────────────────────────
WAREHOUSE: Final[list[PersonConfig]] = [
    {
        "code": "WH_LEAD",
        "username": "wh_lead_lin",
        "full_name": "林家明",
        "email": _email("wh_lead_lin"),
        "role_name": "warehouse",
        "department": "warehouse",
        "title": "倉管組長",
        "hire_date": date(2023, 1, 18),
        "employment_type": "full_time",
        "initial_salary": _d(58000),
        "notes": "倉管組長",
    },
    {
        "code": "WH_02",
        "username": "wh_chen_kai",
        "full_name": "陳凱志",
        "email": _email("wh_chen_kai"),
        "role_name": "warehouse",
        "department": "warehouse",
        "title": "倉管專員",
        "hire_date": date(2023, 3, 6),
        "employment_type": "full_time",
        "initial_salary": _d(45000),
        "notes": None,
    },
    {
        "code": "WH_03",
        "username": "wh_huang_wei",
        "full_name": "黃偉誠",
        "email": _email("wh_huang_wei"),
        "role_name": "warehouse",
        "department": "warehouse",
        "title": "倉管專員",
        "hire_date": date(2023, 5, 15),
        "employment_type": "full_time",
        "initial_salary": _d(43000),
        "notes": None,
    },
    {
        "code": "WH_04",
        "username": "wh_lin_chih",
        "full_name": "林志傑",
        "email": _email("wh_lin_chih"),
        "role_name": "warehouse",
        "department": "warehouse",
        "title": "倉管專員",
        "hire_date": date(2023, 7, 24),
        "employment_type": "full_time",
        "initial_salary": _d(42000),
        "notes": None,
    },
    {
        "code": "WH_05",
        "username": "wh_su_meifen",
        "full_name": "蘇美芬",
        "email": _email("wh_su_meifen"),
        "role_name": "warehouse",
        "department": "warehouse",
        "title": "盤點專員",
        "hire_date": date(2023, 9, 5),
        "employment_type": "full_time",
        "initial_salary": _d(44000),
        "notes": "盤點 / 入庫核對",
    },
    {
        "code": "WH_06",
        "username": "wh_xu_yuhao",
        "full_name": "許育豪",
        "email": _email("wh_xu_yuhao"),
        "role_name": "warehouse",
        "department": "warehouse",
        "title": "物流專員",
        "hire_date": date(2023, 11, 13),
        "employment_type": "full_time",
        "initial_salary": _d(41000),
        "notes": None,
    },
    {
        "code": "WH_07",
        "username": "wh_zhou_yifan",
        "full_name": "周一帆",
        "email": _email("wh_zhou_yifan"),
        "role_name": "warehouse",
        "department": "warehouse",
        "title": "倉管專員",
        "hire_date": date(2024, 1, 22),
        "employment_type": "full_time",
        "initial_salary": _d(42000),
        "notes": None,
    },
    {
        "code": "WH_08",
        "username": "wh_he_yawen",
        "full_name": "何雅雯",
        "email": _email("wh_he_yawen"),
        "role_name": "warehouse",
        "department": "warehouse",
        "title": "盤點專員",
        "hire_date": date(2024, 3, 14),
        "employment_type": "full_time",
        "initial_salary": _d(43000),
        "notes": None,
    },
    {
        "code": "WH_09",
        "username": "wh_wang_chunming",
        "full_name": "王俊銘",
        "email": _email("wh_wang_chunming"),
        "role_name": "warehouse",
        "department": "warehouse",
        "title": "倉管專員",
        "hire_date": date(2024, 5, 27),
        "employment_type": "full_time",
        "initial_salary": _d(40000),
        "notes": None,
    },
    {
        "code": "WH_10",
        "username": "wh_tsai_xiuhua",
        "full_name": "蔡秀華",
        "email": _email("wh_tsai_xiuhua"),
        "role_name": "warehouse",
        "department": "warehouse",
        "title": "倉管專員",
        "hire_date": date(2024, 7, 8),
        "employment_type": "full_time",
        "initial_salary": _d(40000),
        "notes": None,
    },
    {
        "code": "WH_11",
        "username": "wh_chen_jianan",
        "full_name": "陳建安",
        "email": _email("wh_chen_jianan"),
        "role_name": "warehouse",
        "department": "warehouse",
        "title": "物流專員",
        "hire_date": date(2024, 9, 23),
        "employment_type": "full_time",
        "initial_salary": _d(39000),
        "notes": None,
    },
    {
        "code": "WH_12",
        "username": "wh_yang_meiyu",
        "full_name": "楊美玉",
        "email": _email("wh_yang_meiyu"),
        "role_name": "warehouse",
        "department": "warehouse",
        "title": "倉管專員",
        "hire_date": date(2024, 11, 11),
        "employment_type": "part_time",
        "initial_salary": _d(28000),
        "notes": "兼職",
    },
    {
        "code": "WH_13",
        "username": "wh_lu_zhicheng",
        "full_name": "盧志成",
        "email": _email("wh_lu_zhicheng"),
        "role_name": "warehouse",
        "department": "warehouse",
        "title": "倉管專員",
        "hire_date": date(2025, 2, 4),
        "employment_type": "full_time",
        "initial_salary": _d(38000),
        "notes": None,
    },
    {
        "code": "WH_14",
        "username": "wh_song_qiwei",
        "full_name": "宋啟維",
        "email": _email("wh_song_qiwei"),
        "role_name": "warehouse",
        "department": "warehouse",
        "title": "物流專員",
        "hire_date": date(2025, 4, 17),
        "employment_type": "contractor",
        "initial_salary": _d(40000),
        "notes": "外包合約制",
    },
]


# ── Aggregations ─────────────────────────────────────────────────────
PEOPLE: Final[list[PersonConfig]] = [*ADMINS, *MANAGERS, *SALES, *WAREHOUSE]

PERSON_CODES: Final[set[str]] = {p["code"] for p in PEOPLE}


def by_code(code: str) -> PersonConfig:
    for p in PEOPLE:
        if p["code"] == code:
            return p
    raise KeyError(f"unknown person code: {code}")


def by_role(role: RoleName) -> list[PersonConfig]:
    return [p for p in PEOPLE if p["role_name"] == role]


def by_tier(tier: SalesTier) -> list[PersonConfig]:
    return [p for p in SALES if p.get("tier") == tier]


# ── Sanity assertions (run when the module is imported) ──────────────
assert len(ADMINS) == 2, f"expected 2 admins, got {len(ADMINS)}"
assert len(MANAGERS) == 6, f"expected 6 managers, got {len(MANAGERS)}"
assert len(SALES) == 28, f"expected 28 sales, got {len(SALES)}"
assert len(WAREHOUSE) == 14, f"expected 14 warehouse, got {len(WAREHOUSE)}"
assert len(PEOPLE) == 50
assert len(PERSON_CODES) == 50, "person codes must be unique"
assert len({p["username"] for p in PEOPLE}) == 50, "usernames must be unique"
assert len(by_tier("star")) == 3
assert len(by_tier("mid")) == 12
assert len(by_tier("average")) == 9
assert len(by_tier("declining")) == 3
assert len(by_tier("newbie")) == 1
