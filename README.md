# my_erp

一個從零開始打造的小型 **進銷存（Inventory / Sales）+ 應收應付（AR/AP）** ERP 系統，採前後端分離架構，主要使用者介面為**繁體中文**（內建英文切換）。

> **本專案的真正目的：作為 AI agent demo 的模擬資料庫。** 業務邏輯設計得足夠真實（兩段式單據、append-only 紀錄、多角色 RBAC、稅金拆解、AR/AP 帳齡 …），讓 AI agent 能在裡面查資料、做分析、執行跨表推理；但不追求成為「真正商家可上線」的成熟產品。實務上才會在意的細節（PDF 列印 / 印章 / 多倉庫 / 多幣別等）不在近期 backlog。

> 本檔案是給開發者／使用者讀的專案總覽與開發歷程。給 AI agent 看的詳細慣例請見 [`CLAUDE.md`](./CLAUDE.md)。

---

## 1. 專案目標

- 取代手寫帳冊與 Excel，提供老闆／業務／倉管／管理員四種角色各自需要的視角。
- **資料庫可換**：MVP 跑 SQLite，未來透過 `DATABASE_URL` 平移到 PostgreSQL / MySQL 而不改程式碼。
- 多角色 RBAC，前後端皆執行檢查。
- 介面親民，給沒接觸過 ERP 的人也能上手（搭配 `docs/user-guide/manual.html`）。

## 2. 技術棧

| 層      | 工具                                                                              |
| ------- | --------------------------------------------------------------------------------- |
| 後端    | Python 3.12 · FastAPI · SQLAlchemy · Alembic                                      |
| 認證    | JWT + bcrypt（不用 passlib，原因見下方 §開發歷程）                                |
| 前端    | Vite · React 18 · Material-UI (MUI) v5                                            |
| i18n    | react-i18next（zh-TW / en，localStorage 記憶）                                    |
| 報表    | openpyxl（xlsx 串流匯出）                                                         |
| 測試    | pytest（同步 `TestClient`，每測試 truncate temp SQLite，4 角色 fixture）          |
| 環境    | venv + requirements.txt（不使用 poetry / uv）                                     |

## 3. 快速開始

### 後端

```bash
cd backend
python3 -m venv venv
source venv/bin/activate           # PowerShell: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

alembic upgrade head               # 建 schema
python -m app.scripts.seed         # 建 4 個角色 + 初始 admin
python -m app.scripts.seed_menu    # 建預設動態選單樹

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API 文件：http://localhost:8000/docs
- 健康檢查：`/api/v1/health` 與 `/api/v1/health/db`
- 預設 admin：`admin` / `ChangeMe!2026`（依你的 `.env` 為準；上線前請改）

### 前端

```bash
cd frontend
npm install
cp .env.example .env
npm run dev                        # http://localhost:5173
```

### 跑測試

```bash
cd backend && ./venv/bin/pytest    # 111 tests, ~206s
```

---

## 4. 模組總覽

### 業務 / 庫存（進銷存核心）

| 模組         | 重點                                                                                                                                                                            |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 商品 / 分類  | CRUD，`stock_quantity` 只由進銷貨流程改，不開放手動編輯。`low_stock_threshold` 控制低庫存警示。                                                                                  |
| 供應商       | CRUD，含 `payment_terms_days`（影響 AP 到期日）。                                                                                                                               |
| 進貨單       | 兩段式：建草稿 → `POST /receive` 才加庫存並把單價回寫 `product.cost_price`。單號 `PO-YYYYMMDD-####`。可取消（限草稿）。                                                          |
| 客戶         | CRUD，含 `payment_terms_days`、`capital`（資本額）。                                                                                                                            |
| 銷貨單       | 兩段式：建草稿（不檢查庫存，可預下單） → `POST /confirm` 原子驗證 + 扣庫存。`unit_price` **不**回寫商品（商品自己持有牌價）。單號 `SO-YYYYMMDD-####`。`salesperson_id` 與建單者分開，可代鍵。 |
| 庫存查詢     | 即時庫存 + 低庫存篩選 + 警示色。                                                                                                                                                |
| 庫存調整     | append-only 表 `stock_adjustments`，盤盈／盤虧／報廢／其他四種原因，單號 `ADJ-YYYYMMDD-####`。**不能修改、不能刪除**——錯了只能再開反向單抵消。                                  |
| 月報表       | 每商品一列：期初／進貨／銷貨／盤點異動／期末／進銷金額。`closing = current − 月底之後的淨異動`，所以任何月份都自洽。可匯出 xlsx。                                                |
| 業務員報表   | 每位業務當月 order_count / total_qty / total_amount，金額由高到低排序，可匯出 xlsx。                                                                                            |

### 會計 / 財務

| 模組               | 重點                                                                                                                                                                                       |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 應收 / 應付帳款    | SO confirm／PO receive 同交易自動建 `accounts_receivable` / `accounts_payable`。訂單層 `is_tax_inclusive` 控含稅與否，`app/core/tax.py` 做 5% 半進四捨五入拆解。response 含 computed `balance` + `is_overdue`。 |
| 收款 / 付款入帳    | `ar_payments` / `ap_payments`，append-only，狀態自動 `open → partial → paid`。拒過收，拒對已 paid／voided 再收款。單號 `REC-...` / `PAY-...`。                                              |
| 收 / 付款作廢      | `POST /{type}-payments/{id}/void`，同交易內反向更新 paid_amount + 重算 status。idempotent guard（重作廢 409）。前端歷史表已作廢 row 灰化 + 刪除線 + Tooltip。                                |
| AR / AP 帳齡分析   | `GET /accounts-(receivable|payable)/aging?as_of=YYYY-MM-DD`，分桶 `not_due / d1_30 / d31_60 / d61_90 / d90_plus`。前端 `/aging` 頁有 AR/AP 兩 tab + footer 合計。                            |
| 首頁 KPI           | dashboard summary 含本月銷貨／進貨金額、低庫存品項數、draft sales/purchases、AR/AP balance & overdue。HomePage 卡片化顯示，有逾期時紅色 accent。                                            |

### 系統

| 模組         | 重點                                                                                                                                                                                                   |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 使用者管理   | admin only。4 角色：`admin` / `manager` / `sales` / `warehouse`。停用優於刪除；不能刪自己。                                                                                                            |
| 角色查詢     | `/roles`，全員可讀。                                                                                                                                                                                   |
| 動態選單     | 自我參照表 `menu_items`（parent_id CASCADE、label_key/custom_label/icon_name/route_path/required_roles/display_order/is_active）。`GET /menu` 依角色過濾；admin 有 `/menu-management` 頁可拖拉重排與加子節點。 |
| Layout       | MUI Drawer + AppBar，吃 API 的選單樹，Collapse 群組 + localStorage 記憶展開狀態。語言切換 + 使用者選單在 AppBar。                                                                                       |
| i18n         | 所有 UI 字串走 `locales/zh-TW.json` 與 `locales/en.json`，不可硬寫。                                                                                                                                   |

---

## 5. 開發歷程（重要里程碑，時間倒序）

> 完整細節（含每階段 commit / 測試數 / Alembic rev）見 memory `project_future_work.md`。

### 2026-05-19

- 📖 **操作手冊新增「庫存調整（盤點）」章節**：`docs/user-guide/manual.html` 新增 chapter 12（id=`ch-adjust`），原 12/13/14 章順移為 13/14/15；月報那章補「盤點異動」欄位說明。
- 🔐 **per-repo GitHub 帳號隔離**：本 repo 內嵌 `JavisOfWeiYen@` 於 remote URL 並打開 `credential.useHttpPath=true`，全域帳號 `linweiyen` 不動。`main` 已 push 並設好 upstream。
- 📝 撰寫此 README。

### 2026-05-18

- 🧹 **目錄改名 + 累積變更分批 commit**：專案目錄 `my_sales_system` → `my_erp`，工作樹累積的 5 個 Alembic migration + 75 檔變更切兩個 commit（`728a11d` pytest 基礎建設、`5122dfe` Phase 6-9）。

### 2026-05-15 (Phase 6 – 9 累積完成)

- ✅ **Phase 9 動態選單模組**：新表 `menu_items`、依角色過濾 endpoint、admin 拖拉編輯頁、cycle detection、icon 下拉預覽。
- ✅ **Phase 8 三件套**（會計補齊）：
  - Task A：AR / AP 帳齡分析（5 桶 + as_of date + 前端 `/aging` 頁）
  - Task B：首頁 AR / AP KPI（dashboard summary 多 6 欄）
  - Task C：收 / 付款作廢（反向更新 + 重算 status + append-only guard）
- ✅ **Phase 7 收 / 付款入帳**：`ar_payments` / `ap_payments`，status 自動推進、拒過收、append-only。前端 detail dialog 加歷史表 + 記錄收/付款 form。
- ✅ **Phase 6 AR / AP**：SO confirm／PO receive 同交易自動開帳；訂單層 `is_tax_inclusive`；5% 含稅拆解 `core/tax.py`。
- ✅ **pytest 基礎建設**：33 → 最終 111 tests，conftest 用 temp SQLite + Alembic upgrade + 每測試 truncate。
- 🐛 修 `endpoints/customers.py` / `endpoints/suppliers.py` 屬性名稱（rename 漏改造成刪除時 500）。
- ✨ 客戶新增 `capital` 欄位。

### 2026-05-14

- ✅ **盤點 / 庫存調整功能**：append-only `stock_adjustments` 表，月報整合 `adjustment` 欄。
- ✅ **業務員銷售報表**：`/inventory/salesperson-report` + xlsx，ReportsPage Tab 化。
- ✅ **Order rename**：`sales` → `sales_orders`、`purchases` → `purchase_orders`（含 FK / index / class / endpoint 全套）。新增 `sales_orders.salesperson_id`（與 `created_by_id` 分開，主管可代鍵）。
- ✅ **二次 UI 改版**：暖灰 + 石板灰藍 + 天空藍點綴；白底 sidebar；卡片圓角 12px。
- ✅ **MVP 後首版 UI**：ERP 黑灰白風格 + HomePage KPI dashboard；後續再調為暖灰主題。
- 📖 **操作手冊 manual.html**：14 章節（後來加成 15 章），暖灰主題、callout 配色。
- 🛠 **Schema 文件產生器**：`backend/app/scripts/dump_schema_html.py`，從 DB 反射 → `docs/database/schema.html`，含 Mermaid ER 圖。

### 2026-05-13 (MVP 五階段)

- ✅ Phase 0：後端 + 前端骨架
- ✅ Phase 1：JWT 認證 + RBAC（4 角色）
- ✅ Phase 2：商品 + 分類
- ✅ Phase 3：進貨 + 供應商（兩段式入庫）
- ✅ Phase 4：銷貨 + 客戶（兩段式扣庫 + 業務員歸屬）
- ✅ Phase 5：庫存查詢 + 月報表 + xlsx 匯出

---

## 6. 重要設計決策

- **資料庫無關**：所有 DB 存取走 SQLAlchemy ORM，不允許 SQLite-only SQL（如 `AUTOINCREMENT`、SQLite 函式）。Alembic 對 SQLite 用 `render_as_batch=True`，其他 DB 關閉。
- **bcrypt 直用、不要 passlib**：`passlib==1.7.4` 與 `bcrypt>=4.1` 不相容（`AttributeError: module 'bcrypt' has no attribute '__about__'`）。專案在 `core/security.py` 直接用 `bcrypt`，並加 72-byte truncation helper。
- **單號自動產生**：`PO-YYYYMMDD-####` / `SO-YYYYMMDD-####` / `ADJ-...` / `REC-...` / `PAY-...`，可讀且可排序。
- **兩段式單據**：所有交易性單據都是「先建草稿、後執行（receive / confirm）」，方便預下單與權責分離。
- **append-only 紀錄**：庫存調整、收 / 付款一旦存檔就不能改不能刪；錯了用反向單抵銷。
- **稅金內部顯示**：5% 半進四捨五入拆解，**不**做複式記帳。
- **業績歸屬與建單者分開**：`sales_orders.salesperson_id` ≠ `created_by_id`，支援主管代鍵情境。
- **`unit_price` 不回寫商品；`unit_cost` 會回寫商品**（最新成本）——保留毛利分析的彈性，未來再補成本快照。

## 7. 目錄結構

```
my_erp/
├── backend/
│   └── app/
│       ├── main.py              FastAPI factory
│       ├── core/                config / database / security / deps / tax
│       ├── models/              SQLAlchemy ORM（新 model 記得 import 進 __init__.py）
│       ├── schemas/             Pydantic
│       ├── crud/                DB ops
│       ├── api/v1/endpoints/    每個 resource 一個 router
│       └── scripts/             seed.py / seed_menu.py / dump_schema_html.py
├── frontend/
│   └── src/
│       ├── main.jsx             Providers + i18n
│       ├── theme.js             暖灰主題
│       ├── api/                 axios client + per-resource modules
│       ├── contexts/AuthContext.jsx
│       ├── components/Layout.jsx, ProtectedRoute.jsx
│       ├── pages/               Login / Home / Products / Sales / Purchases / ...
│       └── locales/             zh-TW.json / en.json
├── docs/
│   ├── user-guide/manual.html   操作手冊（15 章）
│   └── database/schema.html     ER 圖 + 表格說明（reflect 後 regenerate）
├── CLAUDE.md                    給 AI agent 用的慣例與規則
└── README.md                    本檔
```

## 8. 文件導覽

| 文件                              | 給誰看                                | 內容                                                |
| --------------------------------- | ------------------------------------- | --------------------------------------------------- |
| `README.md`                       | 開發者 / 新加入者                     | 專案總覽 + 歷程（本檔）                             |
| `CLAUDE.md`                       | Claude Code agent                     | 強制慣例、RBAC pattern、bcrypt 注意事項             |
| `docs/user-guide/manual.html`     | 終端使用者（沒接觸過 ERP 的人也能讀） | 15 章操作教學，含截圖示意與 callout                 |
| `docs/database/schema.html`       | 開發者                                | ER 圖 + 每表業務語意（migration 後重跑腳本更新）    |

## 9. Backlog

> 本專案是 AI agent demo 的模擬資料庫（見頁首方塊），因此優先項目偏向「給 AI 更多可查可推理的東西」，而非「真實商家會在意的功能」。

依優先序，動工前需先和使用者對齊：

1. **毛利分析** — 需選成本配對方法：
   - **方案 A（建議）**：銷貨 confirm 當下，快照 `product.cost_price` 寫入 `sales_order_items.unit_cost`。簡單穩定。
   - **方案 B（FIFO）**：批次級庫存表 `stock_lots`，大改動。

低優先（之後再評估）：

- 豐富 seed data（多月份、多客戶、含逾期 AR / 庫存警示 / 作廢付款等情境，讓 AI agent 有東西可查）
- 更多分析型 endpoint（top customers、slow movers、AR 趨勢等）
- 前端 bundle size（目前 ~740 kB，可拆 chunk 或 lazy-load）
- CI / CD（GitHub Actions：pytest + alembic upgrade + lint + build）
- 日報 / 年報（月報邏輯改 `_period_bounds` 即可重用）
- 進貨退回 / 銷貨退回
- 多倉庫、折扣、多幣別（依需求再評估）

**永久延後（不在 AI agent demo 範圍）：**

- PDF 列印（進銷貨單、印章、簽收欄）— 只有真實營運才在意，對 AI demo 無價值。

---

## 10. 環境注意事項

- 程式碼存在 Windows mount（`/mnt/c/...`），透過 WSL 開發。後端也可在 Windows PowerShell 原生跑。
- WSL Ubuntu 首次需要：`sudo apt install -y python3.12-venv`
- `uvicorn --reload` 在 Windows mount 上偶爾因 watchfiles 卡住 2-3 秒，正常。
- 使用者自己跑的 uvicorn / vite dev server 不要 kill，請使用者自行重啟。

## 11. 部署 checklist（未來才需要）

> Dev 階段 localhost HTTP 沒有實質風險（封包不離開 loopback），所以 dev 不用上 HTTPS。
> 但**部署到雲端必須 HTTPS**——TLS 在 reverse proxy 那層終止，應用本身不需要改 code。

部署當天才需要照這份清單一一處理：

### 11.1 前端

- [ ] `cd frontend && npm run build` 產出 `dist/`，由 reverse proxy 或 CDN serve，**不要**上 Vite dev server。
- [ ] 建 `frontend/.env.production`，設 `VITE_API_BASE_URL=https://your-domain/api/v1`（或同網域走 path，例如 `/api/v1`）。
- [ ] SPA fallback：所有非 API 路由都 `try_files {path} /index.html`，否則 React Router 直接刷新會 404。

### 11.2 後端

- [ ] 啟動指令拿掉 `--reload`：`uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers N`（N 視 CPU 數），或用 gunicorn + uvicorn worker。
- [ ] **產生強隨機 `SECRET_KEY`**：`openssl rand -hex 32`，寫進 production `.env`，**絕對不能進版控**。
- [ ] `BACKEND_CORS_ORIGINS` 加上 production domain（去掉 localhost）。
- [ ] `ACCESS_TOKEN_EXPIRE_MINUTES` 視情境調整（demo 可放寬，正式環境應收緊）。
- [ ] 修改預設 admin 密碼，或讓 seed 從 `INITIAL_ADMIN_*` 環境變數讀（已實作）。

### 11.3 資料庫

- [ ] **demo 維持 SQLite 也可以**——`DATABASE_URL=sqlite:///./data/sales_system.db`，volume 掛載 `data/` 確保持久化。
- [ ] **想升級 PostgreSQL**：`DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname`，不用改任何程式碼（架構已 DB-agnostic）。記得 `alembic upgrade head`。

### 11.4 TLS / Reverse proxy（推薦 Caddy）

Caddy 自動處理 Let's Encrypt 簽憑證 + 自動續憑，最省事：

```caddyfile
demo.example.com {
    handle /api/* {
        reverse_proxy localhost:8000
    }
    handle {
        root * /var/www/my_erp/frontend/dist
        try_files {path} /index.html
        file_server
    }
    encode gzip
}
```

或用 nginx + certbot（手動但成熟）。

### 11.5 容器化（可選但推薦）

- [ ] 後端 `Dockerfile`（Python 3.12-slim + requirements + 啟動 uvicorn）
- [ ] 前端用 multi-stage：`node:20` build → `caddy:alpine` 跑 dist（或前端 dist 直接交給 host 的 Caddy）
- [ ] `docker-compose.yml` 串起後端 + Caddy + （可選）PostgreSQL；volume 掛 SQLite db / Caddy data 目錄

### 11.6 主機選擇方向

| 方案                          | 適合                                                          |
| ----------------------------- | ------------------------------------------------------------- |
| VPS（DigitalOcean / Linode）  | 完全控制，最便宜 $4-6/月，自己裝 Docker + Caddy               |
| Fly.io / Render               | 半 PaaS，git push 部署，TLS 自動，但 SQLite 要靠 volume       |
| Cloudflare Tunnel + 自家機器  | 不用買主機、不用開 port，但要保持本機開機                     |

### 11.7 上線後監看

- [ ] 後端 log 拉 stdout（uvicorn 預設）→ docker logs / journalctl
- [ ] `/api/v1/health/db` 接 uptime 監控（UptimeRobot 免費版即可）
- [ ] 定期備份 SQLite（rclone / restic 推 S3）；若用 Postgres 則設 `pg_dump` cron

---

## 12. 授權

內部專案，未對外發佈。
