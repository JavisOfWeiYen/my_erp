# AI Agent Demo Plan

Plan for an on-premise AI agent demo that uses the `seed.db` dataset to
show how a Qwen 2.5-72B-class LLM can augment an ERP — finding business
insights that an ad-hoc UI session would never surface.

- **Audience**: internal / company leadership (老闆 demo)
- **Goal**: prove "AI 補位 ERP" — agent tells the business stories
  buried in the data
- **Stack**: openclaw (agent runtime) + Qwen 2.5-72B (local) + this ERP
- **Permissions**: read-only v1 — agent reports & analyses, does not
  create POs/SOs or void payments

## Architecture decision

**No MCP server. One openclaw skill: `my-erp-analysis`.**

openclaw's skill model (confirmed by user 2026-05-22):
- A skill is a directory containing a `SKILL.md` entry file
- openclaw scans available skills, matches user request against each
  skill's description, picks the best match
- The matched skill's `SKILL.md` is read into context as the playbook
- Reference docs in the same directory are loaded on-demand via the
  Read tool — they don't bloat the initial context

So we ship ONE skill directory. `SKILL.md` is light: identity, when-to-
trigger, decision tree (which reference doc to read for which question
type). The heavy domain content (schema, storylines, examples) lives
in sibling files that the agent pulls in only when needed.

The agent uses openclaw's built-in tools to query the data:

- `exec` — runs shell commands with PTY / background / timeout. We use
  it for both `sqlite3 seed.db "SELECT ..."` (ad-hoc) and `curl
  http://localhost:8000/api/v1/...` (curated reports).
- `read` — pulls in `schema.md` / `storylines.md` / `examples.md` from
  the skill directory on demand.
- `web_search` / `web_fetch` — fallback if the boss asks something
  market-context that isn't in our DB (e.g. "NVIDIA 5070 in 2026 市場
  價多少").

Confirmed against openclaw's tool inventory 2026-05-22:
file ops (read/write/edit), exec + process, web_search / web_fetch,
sessions_* (multi-agent — not used in v1), memory_* (semantic memory —
not used in v1), image (vision — not used in v1).

Why no MCP server:

- Qwen 2.5-72B is capable enough to write SQL or call HTTP directly;
  adding an MCP layer adds latency and a moving part.
- openclaw already handles tool dispatch — duplicating that as MCP is
  pure overhead.
- For internal demo, we own both ends; MCP's portability advantage
  doesn't apply.

A future v2 (POC for external customers) could put the MCP server back
in to standardise tool access across LLM hosts.

## Deployment bundle

On the demo machine:

```
my_erp_demo/
├── backend/                  FastAPI + Alembic + SQLAlchemy + .venv
├── seed.db                   pre-populated dataset (1576 SOs)
├── frontend/dist/            pre-built React SPA (human verification UI)
├── skills/
│   └── my-erp-analysis/      ← THE skill (one directory)
│       ├── SKILL.md          entry: identity, trigger, decision tree
│       ├── schema.md         table/column cheatsheet + query patterns
│       ├── storylines.md     copy of seed/STORYLINES.md (narrative library)
│       └── examples.md       few-shot Q&A traces (matches demo_questions)
├── DEMO_README.md            operator setup + boss-walkthrough order
└── (openclaw + Qwen 2.5-72B installed separately per openclaw's docs)
```

The `skills/my-erp-analysis/` directory is dropped into openclaw's skills
folder (usually `~/.openclaw/skills/` or wherever openclaw is configured
to scan). After that, openclaw auto-detects it on any ERP-related
question.

Backend + frontend + DB run as usual (`uvicorn` + static files via nginx
or `npm preview`). openclaw connects in, loads `skills/` as its working
context, and is ready to answer.

### Why we keep backend + frontend (not just DB)

- Backend codifies non-trivial business logic the agent shouldn't have
  to re-derive: tax inclusivity split, AR/AP aging buckets, weighted
  margin attribution, cost snapshots. If the agent uses backend HTTP,
  it inherits those answers for free.
- Frontend UI is the "human-verifies-agent" channel. When the agent
  says "祥豐 2026-03 開始流失", the boss should be able to click into
  the customer page and see the trend visually. Without the UI, the
  demo is just an LLM hallucinating numbers.

## Skill content design

One skill directory, four files inside.

### `SKILL.md` — entry point (lightest, always in context)

Frontmatter `description` controls openclaw's auto-detection. The body
sets identity + the decision tree pointing to which reference doc to
Read for which question type.

Sketch:

```markdown
---
name: my-erp-analysis
description: |
  Analyse the Taiwan ERP database (my_erp) for sales, margin, AR aging,
  inventory, salesperson performance. Trigger on Chinese or English
  questions about 客戶 / 業務員 / 毛利 / 應收 / 庫存 / 銷售 / 採購
  / SKU / 供應商.
---

# my-erp ERP 分析助理

你是 my_erp 的 AI 業務分析助理。背景：台灣區域 OEM 代理商，授權 NVIDIA /
AMD / Intel / SMC / Dell / HPE，主賣 GPU + AI 伺服器，今天是 2026-05-22。

## 何時用什麼 reference 檔

- 查 schema / 寫 SQL → Read `schema.md`
- 解釋為何某客戶/SKU/業務員行為異常 → Read `storylines.md` 找對應條目
- 範例 Q&A → Read `examples.md`

## 工具選擇

所有資料查詢用 `exec` tool 跑 shell 命令：
- ad-hoc SQL：`sqlite3 ~/my_erp_demo/seed.db "SELECT ..."` (一次性、最快)
- 制式報表 (margin / aging / monthly)：`curl http://localhost:8000/api/v1/...`
- schema.md 對照表會註明每題該用哪個

需要 reference 內容時用 `read` 載入 schema.md / storylines.md / examples.md。

## 鐵則

1. 只讀不寫。看到資料異常只「指出 + 建議」、絕不下單也不改資料。
2. 數字一律 NT$ + 千位逗號。
3. 答業務問題時，**如果有 storyline 對應到該客戶/SKU/業務員，引用劇本
   編號跟一句話摘要**（例如「祥豐電腦在 2026-03 後流失（劇本 3）」）。
4. 沒資料就明說「資料庫沒這欄」、不臆測。
5. 中文回答（除非提問者用英文）；SQL / 欄名保留英文。
```

### `schema.md` — SQL / HTTP cheatsheet（被 Read 引入時才進 context）

Sections:

- **Tables overview**: 5 個核心表（customers / sales_orders /
  sales_order_items / purchase_orders / accounts_receivable）+ 5 個
  輔助表（products / categories / employees / users + role / ar_payments）
- **Computed-field caveats**:
  - `sales_order_items.unit_cost` = confirm 當下的 cost snapshot
  - `accounts_receivable.balance` = `amount_total - paid_amount`
  - `is_overdue` = `due_date < today AND status NOT IN (paid, voided)`
- **Common join patterns** (附 SQL snippet)：SO + 客戶 + 業務員 + 商品
  (revenue + margin) / AR aging / 月毛利趨勢
- **Decimal precision**: 金額 12,2 / 數量 int / margin 算到 2 位
- **HTTP endpoint 對照**: 8 個 curated endpoint（`/analytics/margin/by-customer`、
  `/inventory/monthly-report`、`/accounts-receivable/aging` 等）+ 一段
  「常用報表走 HTTP、自由探索走 SQL」決策準則

### `storylines.md` — narrative library

直接 copy `seed/STORYLINES.md`（32 條劇本 + 7 條跨領域題目）。
Agent 被問「為什麼 H100 毛利這麼低？」時 Read 這個檔、找到劇本 19（AI
熱潮 cost ×1.25）後引用回答。

### `examples.md` — few-shot Q&A traces

每題用 markdown 寫 1 個完整 trace：使用者問題 → agent 思考過程 → 跑了
什麼 SQL / HTTP → 整理出的答案結構。讓 agent 模仿這個 shape 回答其他
類似問題。

七題草稿（順序刻意安排：先靜後動、先個體後跨域）：

1. **「最近 18 個月誰是我們最賺錢的客戶？」**
   → margin by customer top 5；學術 / VIP 對比；引用劇本 8 慧林、1 大同
2. **「2025 上半年 H100 銷售很好，那為什麼毛利反而是負的？」**
   → DC-H100-80 月度 margin trend；引用劇本 19（AI 熱潮 cost ×1.25）
   + 立通是主買家、張俊宏接單
3. **「祥豐電腦最近怎麼了？」**
   → 月度 SO 數 + 付款率走勢；引用劇本 3 + 29（流失 + 付款率歸零）
4. **「應該找誰催收？」**
   → AR aging 旭光 / 祥豐 d60+ d90+；引用劇本 5 + 28
5. **「下季哪些業務員值得加碼？」**
   → 業務員 6 個月 trailing 趨勢；引用劇本 18（蔡明軒爆發）vs 17（劉
   雅婷離職前夕）
6. **「哪些 SKU 我們應該停售或重新議價？」**
   → margin by SKU 排序 + 漲價趨勢；引用劇本 20（NV-5070/5070TI 2026-04
   毛利反轉）
7. **「綜合一句話，我們公司目前最大的隱患是什麼？」**
   → 自由發揮題；agent 應該綜合 (a) 大客戶集中（大同 + 泰昌 + 立通占
   60%+ 營收）(b) 立通退場 + 祥豐流失 (c) NV 漲價未轉嫁 → 答出「客戶
   集中度過高 + 部分 SKU 已賠錢賣，建議分散客群並重啟議價」

每題下方附 **預期 SQL** 或 **預期 HTTP endpoint**，當 agent 第一次跑慢
時可以人工提示「試試 `SELECT ...`」。

`examples.md` 收 3-4 題（不必收滿 7 題、避免 over-fit）— 挑代表性最強
的：H100 毛利反轉 / 祥豐流失 / AR 催收。其他 3 題讓 agent 套泛化。

## Demo script (老闆 walkthrough order)

1. 先給老闆 1 分鐘 frontend tour：「這是 ERP、有這些 module」（建立 demo
   基礎信任：這不是空的）
2. 進 agent chat、問題 1（最熱身、預期答案最確定）
3. 問題 2（戲劇張力最高、H100 賠錢、易引發討論）
4. 問題 3（流失客戶、戲劇）
5. 問題 4（actionable — 老闆看了會想說「明天就找這幾個」）
6. 問題 5（人事 — 老闆通常最在意這塊）
7. 問題 6（SKU/採購）
8. 問題 7（綜合 — agent 自由發揮、展現「跨資料推理」）
9. 老闆自由提問（這時 agent 可能會 miss、留 2 個 fallback 答法在
   `demo_questions.md` 最後）

預期 demo 總長 15-20 分鐘對話、目標每題 30 秒-2 分鐘 agent 思考 +
回答。

## Open questions（規劃完成前要釐清）

1. ~~**openclaw 的 skill 格式具體要什麼樣？**~~  ✅ 2026-05-22 確認：
   directory + `SKILL.md`（frontmatter `name` + `description` 控制
   auto-detection；reference docs 同目錄、用 Read tool 載入）。

2. ~~**openclaw 工具清單**~~ ✅ 2026-05-22 確認：file ops (read/write/
   edit) + exec/process + web_search/web_fetch + sessions_* + memory_*
   + image。SQL/HTTP 策略走 `exec`、reference docs 走 `read`。多 agent
   跟 semantic memory v1 不用。

3. **Qwen 2.5-72B 還是 32B？**
   - 24GB VRAM 跑 72B 要 4-bit AWQ / GPTQ 量化；32B 跑 8-bit 也行
   - 32B 速度快但 tool-chain 推理會差一檔
   - 建議先 72B-AWQ，慢/卡再 fallback 32B

4. **要不要先準備中英文雙語版？**
   - 預設純繁中
   - 若老闆會丟英文題目，SKILL.md 加一句「如果問題是英文，仍以中文
     回答、但 SQL / 欄名保持英文」（已在草稿）

5. **demo 前要不要先「養 cache」？**
   - 預跑 7 個問題、看實際輸出
   - 微調 storylines.md 引用慣例、補 schema.md 漏掉的 join 範例

6. **借用現有 skill 的風格**（新增）：openclaw 內建的
   `ecommerce-sales-analysis` 跟我們的需求最像。能不能先把它的
   `SKILL.md` 給我看一下、確認 frontmatter 跟我們草稿一致 + 偷學它
   的 tone / structure？這 5 分鐘比自己摸索快很多。

## 實作 roadmap

| 階段 | 工作 | 預估 |
|---|---|---|
| 1. 寫 4 個 skill 文件 | system + schema + storylines (copy) + demo_questions | ~2 小時 |
| 2. 部署包打包 | docker-compose 或手寫 systemd unit 起 backend + frontend | ~1 小時 |
| 3. openclaw 整合 | 把 skills/ 餵進 openclaw、跑通第一個問題 | TBD（看 openclaw 文件）|
| 4. 7 題試跑 + 微調 | 每題跑 3 次、看穩定度、調 prompt | ~3 小時 |
| 5. 部署到 demo 機 | 拷 bundle + 起 service + 驗 7 題 | ~1 小時 |

要分幾個 session：建議 2 個。第 1 個寫 skill + 在我們 dev 機跑通 1-2 題；
第 2 個微調 + 打包 + 上 demo 機。
