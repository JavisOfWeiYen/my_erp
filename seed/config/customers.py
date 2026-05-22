"""Customer catalogue — 30 accounts (11 scripted roles + 19 background).

The 11 scripted accounts drive the analytics demo scenarios (RFM, churn,
margin, AR aging, seasonality). The 19 background accounts ensure the
scripted ones don't stick out as obvious outliers in raw lists.

Each entry maps to the backend `CustomerCreate` payload (see
`backend/app/schemas/customer.py`). Extra seed-only fields:

- `code` : internal cross-reference, never sent to API.
- `role` : story archetype; consumed by stories.py / Step 4 timeline to
           pick volume / cadence / margin profile per customer.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Final, Literal, TypedDict


CustomerRole = Literal[
    "vip_stable",        # 大同雲端 — RFM 555
    "vip_volume",        # 泰昌科技 — 量大毛利薄
    "churn",             # 祥豐電腦 — 2026-03 流失
    "hard_negotiator",   # 和欣資訊 — 毛利薄
    "overdue",           # 旭光科技 — 頑固逾期
    "seasonal",          # 宏億通路 — 只 Q4
    "rising",            # 新茂 AI — 2026-01 崛起
    "academic",          # 慧林研究院 — 季度大單高毛利
    "regional_dealer",   # 聖光資訊 — 區域中盤通路
    "ai_cloud",          # 立通科技 — AI 熱潮主角
    "sporadic",          # 達銘電子 — 偶發大單
    "background",        # 其他 19 家
]


class CustomerConfig(TypedDict):
    code: str
    name: str
    contact_name: str | None
    phone: str | None
    email: str | None
    address: str | None
    tax_id: str | None
    capital: Decimal | None
    payment_terms_days: int
    notes: str | None
    role: CustomerRole


def _d(value: str | int) -> Decimal:
    return Decimal(str(value))


CUSTOMERS: Final[list[CustomerConfig]] = [
    # ── 11 劇本角色 ──────────────────────────────────────────────────────
    {
        "code": "DATONG_CLOUD",
        "name": "大同雲端股份有限公司",
        "contact_name": "周宗翰",
        "phone": "02-2655-3300",
        "email": "purchase@datong-cloud.example.com.tw",
        "address": "台北市內湖區瑞光路 200 號 12 樓",
        "tax_id": "84003521",
        "capital": _d(150000000),
        "payment_terms_days": 60,
        "notes": "VIP 穩定戶；每月 5-7 單、從未逾期",
        "role": "vip_stable",
    },
    {
        "code": "TAICHANG_TECH",
        "name": "泰昌科技股份有限公司",
        "contact_name": "羅振宇",
        "phone": "02-8751-9988",
        "email": "ap@taichang-tech.example.com.tw",
        "address": "新北市新店區寶橋路 235 巷 6 號",
        "tax_id": "27895443",
        "capital": _d(300000000),
        "payment_terms_days": 75,
        "notes": "大型 SI；單量大毛利低（~10%）；大買家≠好客戶範例",
        "role": "vip_volume",
    },
    {
        "code": "XIANGFENG_PC",
        "name": "祥豐電腦有限公司",
        "contact_name": "邱志明",
        "phone": "02-2706-4477",
        "email": "buy@xiangfeng-pc.example.com.tw",
        "address": "台北市信義區基隆路一段 178 號 5 樓",
        "tax_id": "53124781",
        "capital": _d(28000000),
        "payment_terms_days": 60,
        "notes": "流失戶；2026-03 後驟降；歷史逾期率 60%",
        "role": "churn",
    },
    {
        "code": "HEXIN_INFO",
        "name": "和欣資訊股份有限公司",
        "contact_name": "賴永福",
        "phone": "03-577-8822",
        "email": "purchase@hexin-info.example.com.tw",
        "address": "新竹市東區慈雲路 56 號",
        "tax_id": "70283199",
        "capital": _d(80000000),
        "payment_terms_days": 45,
        "notes": "議價兇；平均毛利率 7%",
        "role": "hard_negotiator",
    },
    {
        "code": "XUGUANG_TECH",
        "name": "旭光科技有限公司",
        "contact_name": "曾建良",
        "phone": "04-2378-5566",
        "email": "po@xuguang.example.com.tw",
        "address": "台中市西屯區工業區一路 38 號",
        "tax_id": "29761403",
        "capital": _d(15000000),
        "payment_terms_days": 60,
        "notes": "頑固逾期戶；金額不大但每筆都壓滿 60 天",
        "role": "overdue",
    },
    {
        "code": "HONGYI_CH",
        "name": "宏億通路股份有限公司",
        "contact_name": "彭俊德",
        "phone": "02-2932-1188",
        "email": "buyer@hongyi-ch.example.com.tw",
        "address": "台北市文山區羅斯福路六段 142 號",
        "tax_id": "53890227",
        "capital": _d(45000000),
        "payment_terms_days": 30,
        "notes": "季節型；只在 Q4 大量採購",
        "role": "seasonal",
    },
    {
        "code": "XINMAO_AI",
        "name": "新茂 AI 股份有限公司",
        "contact_name": "Karen Tseng",
        "phone": "02-8773-2266",
        "email": "ops@xinmao-ai.example.com.tw",
        "address": "台北市南港區三重路 19-13 號 8 樓",
        "tax_id": "85771049",
        "capital": _d(80000000),
        "payment_terms_days": 60,
        "notes": "新崛起客戶；2026-01 才出現、每月成長 30%；主買 H100",
        "role": "rising",
    },
    {
        "code": "HUILIN_RES",
        "name": "慧林研究院",
        "contact_name": "陳教授",
        "phone": "03-426-7788",
        "email": "purchasing@huilin-res.example.org.tw",
        "address": "桃園市中壢區中大路 300 號",
        "tax_id": "06872133",
        "capital": _d(250000000),
        "payment_terms_days": 90,
        "notes": "學術機構；季度採購工作站；毛利率最高 (~28%)",
        "role": "academic",
    },
    {
        "code": "SHENGGUANG_GM",
        "name": "聖光資訊股份有限公司",
        "contact_name": "施明達",
        "phone": "02-2768-1122",
        "email": "sales@shengguang-info.example.com.tw",
        "address": "台北市松山區八德路四段 760 號",
        "tax_id": "27554683",
        "capital": _d(48000000),
        "payment_terms_days": 45,
        "notes": "北部區域中盤通路；經銷消費級 RTX 50/40 及工作站卡給下游 SI",
        "role": "regional_dealer",
    },
    {
        "code": "LITONG_TECH",
        "name": "立通科技股份有限公司",
        "contact_name": "Ethan Hsu",
        "phone": "02-7705-9988",
        "email": "infra@litong-tech.example.com.tw",
        "address": "台北市信義區松仁路 100 號 18 樓",
        "tax_id": "55028773",
        "capital": _d(450000000),
        "payment_terms_days": 75,
        "notes": "雲服務商；2024-12 ~ 2025-Q3 狂掃 H100、2025-Q4 後沉寂",
        "role": "ai_cloud",
    },
    {
        "code": "DAMING_ELEC",
        "name": "達銘電子股份有限公司",
        "contact_name": "翁世昌",
        "phone": "06-289-7733",
        "email": "buy@daming-elec.example.com.tw",
        "address": "台南市永康區中正南路 880 號",
        "tax_id": "16774229",
        "capital": _d(120000000),
        "payment_terms_days": 60,
        "notes": "偶發大單；每 3-4 月來一張極大單",
        "role": "sporadic",
    },
    # ── 19 背景客戶 ──────────────────────────────────────────────────────
    {
        "code": "BG_YONGSHENG",
        "name": "永盛資訊股份有限公司",
        "contact_name": "蘇文清",
        "phone": "02-2785-3344",
        "email": "po@yongsheng-info.example.com.tw",
        "address": "新北市三重區重新路五段 88 號",
        "tax_id": "29881255",
        "capital": _d(22000000),
        "payment_terms_days": 30,
        "notes": "中型 SI；穩定中量",
        "role": "background",
    },
    {
        "code": "BG_QIYUAN",
        "name": "啟元電子有限公司",
        "contact_name": "鍾政翰",
        "phone": "04-2566-9977",
        "email": "buy@qiyuan-elec.example.com.tw",
        "address": "台中市北屯區崇德路二段 502 號",
        "tax_id": "84456221",
        "capital": _d(18000000),
        "payment_terms_days": 30,
        "notes": "中型 SI",
        "role": "background",
    },
    {
        "code": "BG_HONGYU",
        "name": "宏宇通信股份有限公司",
        "contact_name": "馮聖雄",
        "phone": "07-553-2211",
        "email": "purchasing@hongyu-comm.example.com.tw",
        "address": "高雄市鼓山區中華一路 28 號",
        "tax_id": "27890014",
        "capital": _d(50000000),
        "payment_terms_days": 45,
        "notes": "中型 SI；南部",
        "role": "background",
    },
    {
        "code": "BG_HUACHENG",
        "name": "華成科技股份有限公司",
        "contact_name": "戴文凱",
        "phone": "02-2629-4400",
        "email": "buy@huacheng-tech.example.com.tw",
        "address": "新北市淡水區中正東路二段 99 號",
        "tax_id": "53992188",
        "capital": _d(38000000),
        "payment_terms_days": 45,
        "notes": "中型 SI",
        "role": "background",
    },
    {
        "code": "BG_ZHANYUAN",
        "name": "展遠資訊有限公司",
        "contact_name": "夏立群",
        "phone": "03-318-7755",
        "email": "ops@zhanyuan-info.example.com.tw",
        "address": "桃園市八德區介壽路一段 1180 號",
        "tax_id": "16802491",
        "capital": _d(12000000),
        "payment_terms_days": 30,
        "notes": "小型 SI",
        "role": "background",
    },
    {
        "code": "BG_RUIDA",
        "name": "瑞達電腦有限公司",
        "contact_name": "潘建德",
        "phone": "02-2997-8866",
        "email": "buy@ruida-pc.example.com.tw",
        "address": "新北市新莊區中正路 770 號",
        "tax_id": "70334156",
        "capital": _d(9500000),
        "payment_terms_days": 30,
        "notes": "電競通路",
        "role": "background",
    },
    {
        "code": "BG_DINGXING",
        "name": "鼎興科技股份有限公司",
        "contact_name": "簡明傑",
        "phone": "02-2698-7788",
        "email": "purchase@dingxing.example.com.tw",
        "address": "新北市汐止區新台五路一段 79 號 6 樓",
        "tax_id": "84771502",
        "capital": _d(60000000),
        "payment_terms_days": 60,
        "notes": "中大型 SI",
        "role": "background",
    },
    {
        "code": "BG_LIANCHENG",
        "name": "聯成電腦資訊股份有限公司",
        "contact_name": "施惠雯",
        "phone": "02-2511-3322",
        "email": "po@liancheng-it.example.com.tw",
        "address": "台北市中山區南京東路二段 81 號",
        "tax_id": "27001884",
        "capital": _d(28000000),
        "payment_terms_days": 45,
        "notes": "中型 SI；中山區",
        "role": "background",
    },
    {
        "code": "BG_BAODE",
        "name": "寶德資訊通路股份有限公司",
        "contact_name": "傅子翔",
        "phone": "04-2299-4477",
        "email": "buy@baode-info.example.com.tw",
        "address": "台中市南屯區公益路二段 188 號",
        "tax_id": "53217896",
        "capital": _d(22000000),
        "payment_terms_days": 30,
        "notes": "中部區域通路；經銷 GPU + 入門 AI 推論伺服器給中部企業 IT",
        "role": "background",
    },
    {
        "code": "BG_JIASHENG",
        "name": "佳盛通路科技有限公司",
        "contact_name": "古英傑",
        "phone": "02-2782-1199",
        "email": "buy@jiasheng-channel.example.com.tw",
        "address": "台北市大安區忠孝東路四段 216 號",
        "tax_id": "29772108",
        "capital": _d(14000000),
        "payment_terms_days": 30,
        "notes": "北部中盤通路；經銷 GPU 給小型 SI 與工作室",
        "role": "background",
    },
    {
        "code": "BG_RONGYE",
        "name": "榮業資訊有限公司",
        "contact_name": "丁建宏",
        "phone": "07-228-9933",
        "email": "buy@rongye-info.example.com.tw",
        "address": "高雄市三民區建工路 200 號",
        "tax_id": "84001775",
        "capital": _d(11000000),
        "payment_terms_days": 30,
        "notes": "南部區域通路；經銷 GPU 給高雄一帶 SI",
        "role": "background",
    },
    {
        "code": "BG_WEISHENG",
        "name": "威盛系統整合有限公司",
        "contact_name": "鄒翊豪",
        "phone": "06-298-6655",
        "email": "buy@weisheng-si.example.com.tw",
        "address": "台南市東區東門路一段 320 號",
        "tax_id": "70112486",
        "capital": _d(16000000),
        "payment_terms_days": 30,
        "notes": "南部小型 SI；GPU + 工作站客戶",
        "role": "background",
    },
    {
        "code": "BG_NUOQI",
        "name": "諾奇商業通路股份有限公司",
        "contact_name": "石振凱",
        "phone": "02-8252-7711",
        "email": "buy@nuoqi-channel.example.com.tw",
        "address": "新北市板橋區文化路一段 360 號",
        "tax_id": "27889456",
        "capital": _d(26000000),
        "payment_terms_days": 30,
        "notes": "連鎖企業通路；下游含中小型 SI 與企業 IT 採購",
        "role": "background",
    },
    {
        "code": "BG_HUIDA_UNI",
        "name": "慧達科技大學",
        "contact_name": "資訊處 何主任",
        "phone": "03-892-1166",
        "email": "purchasing@huida-uni.example.edu.tw",
        "address": "花蓮縣壽豐鄉志學村大學路二段 1 號",
        "tax_id": "06112883",
        "capital": _d(180000000),
        "payment_terms_days": 90,
        "notes": "學術；採購流程慢",
        "role": "background",
    },
    {
        "code": "BG_JINGTAI",
        "name": "京泰系統整合股份有限公司",
        "contact_name": "孟廣翊",
        "phone": "02-2776-3344",
        "email": "po@jingtai-si.example.com.tw",
        "address": "台北市大安區光復南路 308 號",
        "tax_id": "84772990",
        "capital": _d(75000000),
        "payment_terms_days": 60,
        "notes": "大型 SI",
        "role": "background",
    },
    {
        "code": "BG_QIANYU",
        "name": "千禧電子有限公司",
        "contact_name": "范俊偉",
        "phone": "02-2563-8877",
        "email": "buy@qianyu-elec.example.com.tw",
        "address": "台北市中山區民生東路二段 161 號",
        "tax_id": "53449682",
        "capital": _d(11000000),
        "payment_terms_days": 30,
        "notes": "中型 SI",
        "role": "background",
    },
    {
        "code": "BG_HAOXIANG",
        "name": "豪翔電腦有限公司",
        "contact_name": "藍正謙",
        "phone": "07-389-2211",
        "email": "buy@haoxiang-pc.example.com.tw",
        "address": "高雄市左營區博愛二路 290 號",
        "tax_id": "27108455",
        "capital": _d(8500000),
        "payment_terms_days": 30,
        "notes": "中型通路；南部",
        "role": "background",
    },
    {
        "code": "BG_KAIYANG",
        "name": "凱揚智能股份有限公司",
        "contact_name": "白舒怡",
        "phone": "03-668-9933",
        "email": "ops@kaiyang-ai.example.com.tw",
        "address": "新竹縣竹北市光明六路 60 號",
        "tax_id": "84669011",
        "capital": _d(55000000),
        "payment_terms_days": 45,
        "notes": "AI 應用整合商",
        "role": "background",
    },
    {
        "code": "BG_TAIANG",
        "name": "泰昂電腦工程有限公司",
        "contact_name": "唐宇翔",
        "phone": "04-2700-5566",
        "email": "buy@taiang-eng.example.com.tw",
        "address": "台中市西區台灣大道二段 503 號",
        "tax_id": "27885614",
        "capital": _d(13500000),
        "payment_terms_days": 30,
        "notes": "中部 SI",
        "role": "background",
    },
]


assert len(CUSTOMERS) == 30, f"expected 30 customers, got {len(CUSTOMERS)}"
assert len({c["code"] for c in CUSTOMERS}) == 30, "customer codes must be unique"


CUSTOMER_CODES: Final[set[str]] = {c["code"] for c in CUSTOMERS}


def by_code(code: str) -> CustomerConfig:
    for c in CUSTOMERS:
        if c["code"] == code:
            return c
    raise KeyError(f"unknown customer code: {code}")


def by_role(role: CustomerRole) -> list[CustomerConfig]:
    return [c for c in CUSTOMERS if c["role"] == role]
