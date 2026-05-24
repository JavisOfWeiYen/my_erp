# Seed Storylines

This document catalogues the scripted scenarios baked into `seed.db` by
the 18-month timeline generator (Step 4). Use it as a reference when
designing the AI agent demo — every storyline below has a definite
question, characters, time window, and a query/observation that proves
it shows up in the data.

- **Timeline window**: 2024-12-01 → 2026-05-31 (18 months)
- **Data shape**: 97 POs / 1576 SOs confirmed / 9 SOs skipped (stockout) /
  3712 SO line items / 1576 ARs (1549 paid + 27 still open) / 1551 AR
  payments (2 voided) / 97 APs (all paid) / 97 AP payments / 6 stock
  adjustments / 50 employees / 30 customers / 6 suppliers / 37 SKUs /
  5 categories

---

## Customer storylines

### 1. VIP 穩定戶 — 大同雲端
- **角色**: `vip_stable`, RFM 555 candidate
- **Behaviour**: 5-7 orders/month every month, NT$ 300k–1.2M average, 12-18% margin, 0% overdue
- **Total in dataset**: ~112 orders, ~NT$ 644M revenue (#1 customer)
- **Demo question**: "誰是我們最穩定的 VIP？" → 大同雲端
- **Observation queries**:
  - Group SOs by customer → 大同 always #1 revenue
  - AR aging for 大同 → all rows in `not_due` bucket

### 2. 量大毛利薄 — 泰昌科技
- **角色**: `vip_volume`
- **Behaviour**: 4-6 orders/month, NT$ 500k–1.5M, 8-12% margin, 15% overdue
- **Total**: ~91 orders, ~NT$ 439M revenue (#2), margin ~9.16%
- **Demo question**: "大買家是不是好客戶？" → 泰昌營收第二大但毛利率墊底（9% vs VIP avg 13%）
- **Observation**: 比較 customer revenue Top 5 跟 margin Top 5 — 泰昌出現在 revenue Top 但不在 margin Top

### 3. 流失戶 — 祥豐電腦
- **角色**: `churn`
- **Behaviour**: 5-8 orders/month before 2026-03; 2026-03 onwards drops to 0-2 (override in `CUSTOMER_STORY_OVERRIDES`); 60% historical overdue
- **Demo question**: "誰要流失了？" → 祥豐電腦 — RFM 在 2026-05 應該掉到 R1F1M1 區段
- **Observation queries**:
  - Monthly SO count for 祥豐 → 2026-02 ≥ 5, 2026-03+ ≤ 2
  - Compute Recency (days since last order) as of 2026-05-31 → 祥豐 高

### 4. 議價兇毛利薄 — 和欣資訊
- **角色**: `hard_negotiator`
- **Behaviour**: 4-6 orders/month, target margin **5-9%** (lowest in dataset), 10% overdue
- **Total**: 觀測毛利率 6.38% — 明顯低於 VIP avg 13.3%
- **Demo question**: "哪個客戶議價最兇/最不賺錢？" → 和欣
- **Observation**: 按客戶看 margin 排序 → 和欣在最低段

### 5. 頑固逾期戶 — 旭光科技
- **角色**: `overdue`
- **Behaviour**: 1-3 orders/month, NT$ 40k–120k, **85% overdue rate**（最高）
- **Total**: ~43 小單, ~NT$ 3.7M revenue（最後一名）
- **Demo question**: "誰的應收最難收？" → 旭光
- **Observation**: AR aging 按客戶分組，旭光 90+ days bucket 集中

### 6. 季節型 — 宏億通路
- **角色**: `seasonal` + `quarterly_burst: (4, (5, 8))`
- **Behaviour**: Q1-Q3 幾乎不出現（0-1/month），Q4 一口氣 5-8 單
- **Demo question**: "誰只 Q4 出現？" → 宏億
- **Observation**: 宏億按月分析 → 2024-12 / 2025-10/11/12 數量遠高於其他月

### 7. 新崛起客戶 — 新茂 AI
- **角色**: `rising`, `active_window=(2026-01, 2026-05)`, `monthly_growth_pct=1.30`
- **Behaviour**: 2026-01 才出現，每月複利成長 30%；主買 H100 + AI 整機
- **Total**: ~11 orders 但 ~NT$ 94M (avg NT$ 8.5M/order)
- **Demo question**: "近期哪個客戶在快速成長？" → 新茂 AI
- **Observation queries**:
  - 2026-01 才有第一筆 SO
  - 2026-01 ~ 05 月份營收呈幾何成長

### 8. 學術高毛利 — 慧林研究院 / 慧達科技大學
- **角色**: `academic` + `quarterly_burst: (1, (2, 3))`
- **Behaviour**: 季度集中採購，target margin **22-30%**（全資料庫最高）
- **Total**: 慧林觀測 21.12% margin — 約等於最高段
- **Demo question**: "學術客戶毛利率為何最高？" → 採購流程慢但價格不敏感，工作站卡為主
- **Observation**: 按客戶分析 margin → 慧林 / 慧達 排前兩名

### 9. 區域中盤 — 聖光資訊
- **角色**: `regional_dealer`
- **Behaviour**: 3-8 orders/month, 多 SKU 混單, 12-18% margin
- **Demo question**: "通路盤跟直客比 order pattern 差在哪？"
- **Observation**: 聖光 average order value 低、line items 多；對比直客（單筆大、line items 少）

### 10. AI 熱潮主角 — 立通科技
- **角色**: `ai_cloud` + `CUSTOMER_STORY_OVERRIDES` 從 2025-10 起遞減到 0
- **Behaviour**: 2024-12 ~ 2025-Q3 狂掃 H100/H100 SXM；2025-Q4 ~ 2026-05 沉寂
- **Total**: ~46 orders 但 ~NT$ 432M（avg NT$ 9.4M/order）
- **Demo question**: "為什麼 H100 銷售在 2025-Q4 後驟降？" → 立通退場
- **Observation queries**:
  - H100 SKU 按月看 SO 數 → 2024-12 ~ 2025-09 高、2025-10 後跌
  - 立通月營收 → 2025-Q3 高、2025-Q4 後驟降

### 11. 偶發大單 — 達銘電子
- **角色**: `sporadic` + `big_order_months=[2025-03, 2025-07, 2025-11, 2026-03]`
- **Behaviour**: 平常 0-1 單，每 3-4 月來一張 NT$ 800k–1.8M 大單
- **Demo question**: "誰是冷不防來大單的客戶？" → 達銘
- **Observation**: 達銘 monthly revenue → 4 月份明顯高峰

---

## Salesperson storylines

業務員加權主要由 `tier` (`star=4.0 / mid=2.0 / average=1.0 / declining=1.3 / newbie=0.4`) +
`SALES_PERSONAL_EVENTS` 月份 multiplier 決定。

### 12. 明星業務員 Top 3
- **角色**: `star` tier (3 人)
- **資料**: 張俊宏 (SLS_STAR_1) / 李曉雯 (SLS_STAR_2) / 王智浩 (SLS_STAR_3)
- **Demo question**: "業績最強的業務是誰？" → 張俊宏 ~NT$ 203M / 王智浩 ~NT$ 165M / 李曉雯 ~NT$ 134M

### 13. 明星 #1 AI 熱潮加成 — 張俊宏
- **Event**: `SLS_STAR_1, months=[2025-01,02,03], multiplier=1.40`
- **Story**: 負責立通，AI 熱潮 H100 訂單帶飛
- **Demo question**: "張俊宏為什麼是 #1？"
- **Observation**: 張俊宏在 2025-Q1 月度業績比其他月份明顯高峰

### 14. 明星 #2 病假 — 李曉雯
- **Event**: `SLS_STAR_2, months=[2025-08, 2025-09], multiplier=0.20` + `[2025-10], 0.75`
- **Story**: 病假兩個月後復健
- **Demo question**: "李曉雯為什麼 #3 不是 #2？" → 8/9 月幾乎沒出單
- **Observation queries**:
  - 李曉雯 monthly orders → 2025-08 / 09 明顯掉到 1-2 單
  - 2025-10 恢復約 7-8 成

### 15. 衰退軌跡 — 黃秀美
- **Event**: `SLS_DECLINE_1`, multipliers 跨 8 個月遞減
  - 2025-07/08/09: 0.85
  - 2025-10/11/12: 0.70
  - 2026-01 ~ 05: 0.50
- **Demo question**: "誰的業績在持續下滑？" → 黃秀美
- **Observation**: 6 個月滾動平均逐月下降

### 16. 衝突丟客 — 吳建華
- **Event**: `SLS_DECLINE_2, months=2026-01~05, multiplier=0.50`
- **Story**: 跟和欣衝突丟客戶
- **Demo question**: "2026 年衰退最快的業務？" → 吳建華 + 劉雅婷

### 17. 離職前夕 — 劉雅婷
- **Event**: `SLS_DECLINE_3, months=2026-04/05, multiplier=0.00`
- **Story**: 完全沒開單
- **Demo question**: "誰可能要離職？" → 劉雅婷（2026-04 起 0 單）
- **Observation**: 最近 60 天無 SO 紀錄的業務

### 18. 新人崛起 — 蔡明軒
- **Event**: `SLS_NEWBIE, hire_date=2026-01-15`, multipliers:
  - 2026-01: 0.40 (慢熱)
  - 2026-02/03: 0.80 (跟單熟悉)
  - 2026-04/05: 2.50 (爆發)
- **Story**: 入職 5 個月、最後兩月業績挑戰中段班
- **Demo question**: "誰是最有潛力的新人？" → 蔡明軒
- **Observation queries**:
  - 蔡明軒月度業績曲線：0 → 慢熱 → 爆發
  - 2026-04/05 業績排名跟 2026-01 對比

---

## Cost / Margin storylines

### 19. AI 熱潮 H100 毛利反轉 ⭐⭐⭐
- **Event**: `COST_HIKE_EVENTS` DC-H100-80 / DC-H100-SXM 2024-12 起 ×1.25；2025-10 起 ×0.80（回穩）
- **Story**: AI 熱潮供應緊、NVIDIA 漲 25%；我們價單沒漲 → 賠錢賣 H100
- **Demo question**: "為什麼 2024-12 ~ 2025-09 H100 毛利是負的？2025-10 怎麼回穩？"
- **Observation queries** (極具戲劇張力):
  - DC-H100-80 月度 (price, cost, margin):
    - 2024-12 ~ 2025-09: cost = 1,050,000, price ≈ 950,000, **margin -10% ~ -15%（虧錢賣）**
    - 2025-10 起 cost 回 840,000, price 不變 ≈ 950,000, **margin +10% ~ +15%**
  - 立通科技 (主要 H100 買家) 在這段時間貢獻營收最大、卻是公司最虧的客戶

### 20. NVIDIA GeForce 漲價壓縮毛利 ⭐⭐⭐
- **Event**: `COST_HIKE_EVENTS` NV-5070 / NV-5070TI / NV-4080S / NV-4070S 2026-04 起 ×1.20、2026-05 又 ×1.20（累積 1.44）
- **Story**: NVIDIA 區域配額調整、進價短期上修 44%；客戶價單沒動 → 部分 SKU 變成賠錢賣
- **Demo question**: "為什麼 2026-04/05 這幾個 GeForce SKU 毛利突然崩盤？"
- **Observation queries** (NV-5070 為例):
  - 2026-03: price 19,594 / cost 16,500 / **margin 15.79%**
  - 2026-04: price 19,442 / cost 19,800 / **margin -1.84%**
  - 2026-05: price 19,552 / cost 23,760 / **margin -21.52%**（賣一張賠 4,200）
- **Aggregate 影響**: 2026-Q1 平均毛利 14.02% vs Q2 (Apr-May) 12.43% — 差距 1.59 pp（KPI 目標 2pp 因 SKU 涵蓋面只 ~2% 總營收沒過，但 per-SKU 故事完整）

### 21. 角色毛利分布（pricing power 對照）
- 慧林研究院 (academic): **21.12%** — 採購流程慢、價格不敏感
- 大同雲端 (vip_stable): **13.32%** — 穩定戶合理定價
- 泰昌科技 (vip_volume): **9.16%** — 量大議價空間大
- 和欣資訊 (hard_negotiator): **6.38%** — 議價兇
- **Demo question**: "不同類型客戶我們賺的差多少？什麼客戶才是好客戶？"

---

## Stock / Supply storylines

### 22. RTX 5090 上市初期供不應求
- **Event**: `STOCKOUT_EVENTS` NV-5090 2025-01/02 severity 0.25 (received qty 砍到 25%)
- **Result**: 2025-01 有 5 張 SO confirm 失敗（cancel）、2025-02 有 4 張
- **Demo question**: "RTX 5090 上市那兩個月為什麼掉單？"
- **Observation**: 2025-01 / 02 月 cancelled SOs 比其他月高；NV-5090 那兩個月庫存追不上

### 23. NV-5070 缺貨窗口
- **Event**: NV-5070 / NV-5070TI 2025-09 + 2026-02 severity 0.10
- **Story**: NVIDIA 端晶片 supply 緊
- **Demo question**: "2025-09 / 2026-02 為什麼有 SO 開不出來？"
- **Observation**: 那兩個月 NV-5070 / 5070TI 庫存接近 0、low_stock_threshold 觸發

---

## Seasonality storylines

### 24. 季度週期性
- **Multipliers**: Q1=0.90 / Q2=1.00 / Q3=0.95 / **Q4=1.35**
- **Demo question**: "我們公司 Q4 vs Q1 業績差多少？"
- **Observation**: 同年 Q4 月份 SO 數 比 Q1 月份多約 35-50%（2024-12 vs 2025-01: 120 vs 80 = 1.50x）

### 25. 學術季度集中採購
- 慧林 / 慧達 `quarterly_burst (Q1, (1-3))`
- **Demo question**: "學術機構什麼時候採購？" → Q1（年度預算下達後）
- **Observation**: 慧林 2025-01/02/03 SO 數遠高於其他月

### 26. 通路 Q4 旺季
- 宏億 `quarterly_burst (Q4, (5-8))`
- **Demo question**: "通路型客戶什麼時候採購？" → Q4
- **Observation**: 宏億 2024-12 / 2025-10/11/12 月度單量遠高於 Q1/2/3

---

## AR / AP storylines (Step 5 完成)

Step 5 已套用：1551 AR 付款 / 97 AP 付款 / 6 盤點 / 2 收款作廢。AR 付款時機依
`seed_events.PAYMENT_PROFILE_BY_ROLE` 按客戶 role 抽樣（早付 / 準時 / 1-30 晚 / 30-100 晚 / 不付）。

### 27. 大同雲端零逾期戶 ✅ 驗證通過
- 109 筆 AR 全 paid，沒有任何遲付
- `vip_stable` profile: pay_rate=1.00, lateness=(-10, -1) — 全部早付 1-10 天
- **Demo question**: "誰是最完美的付款客戶？" → 大同

### 28. 旭光頑固逾期戶 ✅ 驗證通過
- 40 筆 AR 中：4 準時 + 4 d1-30 + 9 d31-60 + 9 d61-90 + 3 d90+ + **11 完全沒付**
- `overdue` profile: pay_rate=0.70（30% 不付）, late_split (15% 準時 + 85% 45-100 天)
- **Demo question**: "哪個客戶最該停信用？" → 旭光（27% 從沒付過 + 大量壓爆 90 天）

### 29. 祥豐流失型付款劇本 ✅ 驗證通過
- 96 筆 AR 中 82 paid / 14 still open
- 月度付款率走勢：
  - 2024-12 ~ 2026-01: 大多 80-100%
  - 2026-02: 60%（churn 基準）
  - **2026-03: 0%**（XIANGFENG override 觸發 — 流失後也停付）
  - 2026-04: 1 筆樣本 100%（剩太少看不出）
- **Demo question**: "祥豐除了下單變少，付款狀況也變了嗎？" → 2026-03 後付款率歸零，更狠的流失證據

### 30. AR 收款作廢 ✅ 驗證通過
- 2 筆完整作廢：
  - REC-20250927-0003: 諾奇商業通路 (BG_NUOQI) 2025-09 客戶退票
  - REC-20260213-0001: 豪翔電腦 (BG_HAOXIANG) 2026-02 誤入帳沖正
- **Demo question**: "今年有多少筆收款被作廢？" → 2 筆
- 注意 backend 編號 generator 正確用 paid_at 寫日期 prefix（不像 AR.ar_number 用今天）

### 31. AR aging d90+ 集中度 ✅ 驗證通過 (22 筆 / KPI ≥ 5)
- 22 筆 AR 在 2026-05-22 still open 且 due_date 早於 2026-02-21
- 主要來源：旭光 + 祥豐 + 各 role 的 10-20% 慢付戶
- **Demo question**: "我們最舊的應收有多少？誰欠最久？"

### 32. AP 全準時付款（demo 對照組）
- 97 筆 AP 全 paid，提早 0-5 天付（demo 對照組，不放戲劇）
- **Demo 反襯**: 如果問 "我們對供應商準時嗎？" → 答 yes，反襯出客戶端有戲

---

## Cross-cutting demo questions

這幾條題目橫跨多個劇本，最能展示 AI agent 整合能力：

1. **"找出公司最賺錢的客戶+業務員組合"** — 結合 customer margin 排序 + salesperson revenue 排序 + 交叉表
2. **"2025 年 H100 為什麼讓我們虧錢，最終誰扛了損失？"** — H100 cost hike + 立通 / 張俊宏 高營收低毛利
3. **"預測下季哪個業務員會領跑？"** — 結合 newbie growth curve (蔡明軒) + 衰退軌跡 (黃秀美 / 吳建華 / 劉雅婷) + 季節性
4. **"列出本月所有應該提早催收的應收"** — AR aging + 客戶歷史 overdue_rate
5. **"哪些 SKU 是我們應該砍掉的『策略性虧損』？"** — 商品 margin 排序、結合銷量 → DC-H100-80 在 2025 上半年、NV-5070 在 2026-04/05
6. **"我們的營收結構在 18 個月內怎麼變？"** — Category mix 變化（AI_SERVER 上升、Consumer GPU 穩定、Datacenter 大起大落）
7. **"識別異常 SO/PO"** — margin < 0 的單、stockout 期間的缺貨單

---

## Implementation notes

- **Story 編號** 對應 `seed/config/stories.py` 的事件清單。要新增劇本就改那個檔。
- **Margin compression KPI 部分達成**: 1.59pp（目標 2pp）。要拉到 2pp 需要把 cost hike 擴大到更多 NV consumer SKU（NV-5060TI / NV-5060 / NV-4070 / NV-4060TI）。決定先收尾不做。
- **`so_number` / `po_number` / `ar_number` / `ap_number` 全部用今天日期** (2026-05-22) 當 prefix——backend 編號 generator 沒收 ordered_at/issued_at。Step 6 會寫 SQL backfill 重編。
- **26 筆 SO confirmed_at 落在 today (2026-05-22) 之後** — 因為 TIMELINE_END=2026-05-31 但今天是 2026-05-22。對分析無影響、demo 視為「未來訂單」。
