"""Generate a single-file HTML schema doc from live DB introspection.

Usage:
    python -m app.scripts.dump_schema_html              # writes ../docs/database/schema.html
    python -m app.scripts.dump_schema_html /tmp/x.html  # custom output path

The output is fully self-contained (inline CSS + mermaid via CDN), so it can be
opened directly in a browser.
"""

from __future__ import annotations

import datetime as _dt
import html
import sys
from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.engine import Engine, Inspector

import app.models  # noqa: F401 — ensure metadata is populated for the engine
from app.core.database import engine

# ---- Per-table editorial metadata (label + business notes). Adding entries
#      here just enriches the HTML; missing tables still render fine.
TABLE_LABELS: dict[str, str] = {
    "roles": "角色主檔",
    "users": "使用者帳號",
    "categories": "商品分類",
    "products": "商品主檔",
    "suppliers": "供應商主檔",
    "purchase_orders": "進貨單表頭",
    "purchase_order_items": "進貨單明細",
    "customers": "客戶主檔",
    "sales_orders": "銷貨單表頭",
    "sales_order_items": "銷貨單明細",
    "stock_adjustments": "庫存調整 / 盤點紀錄",
}

TABLE_NOTES: dict[str, str] = {
    "products": """\
<b>業務規則：</b>
<ul>
  <li><code>stock_quantity</code> 只能透過 <code>POST /purchase-orders/{id}/receive</code> 加庫存 / <code>POST /sales-orders/{id}/confirm</code> 扣庫存。Products API 的 update 不會動它。</li>
  <li><code>cost_price</code> 在 purchase 收貨時，會以該明細的 <code>unit_cost</code> 寫回；<code>unit_price</code> 不會被 sale 寫回。</li>
  <li><code>low_stock_threshold</code> 設 0 等於關閉低庫存警示。</li>
</ul>""",
    "purchase_orders": """\
<b>兩階段流程：</b>
<ul>
  <li><code>POST /purchase-orders</code> → 建立 draft</li>
  <li><code>POST /purchase-orders/{id}/receive</code> → 翻成 received + 加庫存 + 寫回 <code>product.cost_price</code></li>
  <li><code>POST /purchase-orders/{id}/cancel</code> → 翻成 cancelled（只允許 draft）</li>
  <li>只有 draft 可編輯。</li>
</ul>""",
    "sales_orders": """\
<b>兩階段流程：</b>
<ul>
  <li><code>POST /sales-orders</code> → 建立 draft（不檢查庫存）</li>
  <li><code>POST /sales-orders/{id}/confirm</code> → 驗證 <code>stock_quantity ≥ quantity</code> 並原子扣庫存 + 寫 <code>confirmed_at</code></li>
  <li><code>POST /sales-orders/{id}/cancel</code> → 翻成 cancelled（只允許 draft）</li>
  <li><code>unit_price</code> 不會被寫回 product；商品自己持有牌價。</li>
</ul>
<b>salesperson_id vs created_by_id：</b>
<ul>
  <li><code>salesperson_id</code> = 業績歸屬，用來統計每位業務的銷售。</li>
  <li><code>created_by_id</code> = 實際操作鍵入這張單的人。主管代鍵時兩者會不同。</li>
</ul>""",
    "roles": """\
<b>種子資料：</b>四個固定角色 — <code>admin</code> / <code>manager</code> / <code>sales</code> / <code>warehouse</code>，由 <code>python -m app.scripts.seed</code> 建立。""",
    "users": """\
<b>密碼：</b>直接用 <code>bcrypt</code> 套件雜湊（**不**經過 passlib，避免 passlib 1.7.4 + bcrypt 4.1 的相容問題）。""",
    "stock_adjustments": """\
<b>用途：</b>記錄盤點 / 庫存調整。每一筆 = 一個商品在一個時間點被人為調整。
<ul>
  <li>立即生效 — 建立的同時 <code>product.stock_quantity</code> 會被加上 <code>change_qty</code>。</li>
  <li><strong>不可編輯、不可刪除</strong>。寫下去就是審計憑證。</li>
  <li>會擋庫存變負（<code>after_qty</code> CHECK ≥ 0）。</li>
  <li>單號自動產生 <code>ADJ-YYYYMMDD-####</code>。</li>
  <li>RBAC：admin / manager / warehouse 可建；全員可讀。</li>
</ul>
<b>原因類型：</b>
<ul>
  <li><code>surplus</code> 盤盈 — 盤點發現比系統多</li>
  <li><code>shortage</code> 盤虧 — 盤點發現比系統少</li>
  <li><code>scrap</code> 報廢 — 損壞 / 過期</li>
  <li><code>other</code> 其他 — 補正 / 樣品 / 內部使用</li>
</ul>""",
}

COLUMN_NOTES: dict[tuple[str, str], str] = {
    # (table, column) -> note text shown in the rightmost column
    ("users", "hashed_password"): "bcrypt（不用 passlib）",
    ("users", "is_active"): "default true",
    ("products", "unit_price"): "售價，default 0",
    ("products", "cost_price"): "成本，receive 時寫回",
    ("products", "stock_quantity"): "僅 purchase/sale 流程可寫",
    ("products", "low_stock_threshold"): "0 = 關閉低庫存警示",
    ("products", "barcode"): "可空",
    ("products", "unit"): 'default "個"',
    ("purchase_orders", "po_number"): "PO-YYYYMMDD-####",
    ("purchase_orders", "status"): "draft / received / cancelled",
    ("purchase_orders", "ordered_at"): "下單時間",
    ("purchase_orders", "received_at"): "receive 時寫入",
    ("purchase_orders", "created_by_id"): "建單者",
    ("sales_orders", "so_number"): "SO-YYYYMMDD-####",
    ("sales_orders", "status"): "draft / confirmed / cancelled",
    ("sales_orders", "salesperson_id"): "業績歸屬（可與建單者不同）",
    ("sales_orders", "created_by_id"): "實際建單者",
    ("sales_orders", "confirmed_at"): "confirm 時寫入",
    ("purchase_order_items", "quantity"): "CHECK > 0",
    ("purchase_order_items", "unit_cost"): "CHECK >= 0",
    ("purchase_order_items", "subtotal"): "= quantity × unit_cost",
    ("sales_order_items", "quantity"): "CHECK > 0",
    ("sales_order_items", "unit_price"): "CHECK >= 0",
    ("sales_order_items", "subtotal"): "= quantity × unit_price",
    ("suppliers", "tax_id"): "統編",
    ("customers", "tax_id"): "統編",
    ("roles", "name"): "admin / manager / sales / warehouse",
    ("stock_adjustments", "adjustment_number"): "ADJ-YYYYMMDD-####",
    ("stock_adjustments", "change_qty"): "正 = 加 / 負 = 扣，CHECK ≠ 0",
    ("stock_adjustments", "after_qty"): "= before_qty + change_qty，CHECK ≥ 0",
    ("stock_adjustments", "reason"): "surplus / shortage / scrap / other",
    ("stock_adjustments", "operator_id"): "誰按的這次調整",
    ("stock_adjustments", "adjusted_at"): "建立時間戳記",
}

# Render order for the table cards (and the ER diagram entity blocks).
TABLE_ORDER = [
    "roles",
    "users",
    "categories",
    "products",
    "suppliers",
    "purchase_orders",
    "purchase_order_items",
    "customers",
    "sales_orders",
    "sales_order_items",
    "stock_adjustments",
]


def _normalize_type(t: str) -> str:
    # Friendlier display: VARCHAR(128) -> varchar(128), DATETIME -> timestamptz
    t = t.lower()
    if t in ("datetime", "timestamp"):
        return "timestamptz"
    return t


def _mermaid_type(t: str) -> str:
    """Map SQL types to mermaid-erDiagram friendly tokens."""
    t = t.lower()
    if t.startswith("varchar") or t.startswith("char") or t.startswith("text"):
        return "string"
    if t.startswith("numeric") or t.startswith("decimal"):
        return "numeric"
    if t.startswith("int") or t == "integer":
        return "int"
    if t in ("datetime", "timestamp") or t.startswith("timestamp"):
        return "datetime"
    if t == "boolean":
        return "bool"
    return t


def _column_flags(table: str, col: dict, insp: Inspector) -> dict[str, bool]:
    name = col["name"]
    pk_cols = set(insp.get_pk_constraint(table)["constrained_columns"] or [])
    fk_cols: set[str] = set()
    for fk in insp.get_foreign_keys(table):
        for c in fk["constrained_columns"]:
            fk_cols.add(c)
    unique_cols: set[str] = set()
    for u in insp.get_unique_constraints(table):
        for c in u["column_names"]:
            unique_cols.add(c)
    indexed_cols: set[str] = set()
    for i in insp.get_indexes(table):
        if i["unique"]:
            # Reflected unique indexes (the common case in SQLite) also act as UNIQUE.
            for c in i["column_names"]:
                unique_cols.add(c)
        for c in i["column_names"]:
            indexed_cols.add(c)
    return {
        "pk": name in pk_cols,
        "fk": name in fk_cols,
        "unique": name in unique_cols,
        "indexed": name in indexed_cols and name not in pk_cols,
        "notnull": not col["nullable"],
        "nullable": col["nullable"],
    }


def _fk_target(table: str, col: str, insp: Inspector) -> str | None:
    for fk in insp.get_foreign_keys(table):
        if col in fk["constrained_columns"]:
            ondelete = fk.get("options", {}).get("ondelete")
            target = f"{fk['referred_table']}.{fk['referred_columns'][0]}"
            return f"→ {target}" + (f" ({ondelete})" if ondelete else "")
    return None


# ---- Mermaid ER diagram

def render_mermaid(engine: Engine, insp: Inspector) -> str:
    relations: list[str] = []
    blocks: list[str] = []
    for t in TABLE_ORDER:
        if t not in insp.get_table_names():
            continue
        for fk in insp.get_foreign_keys(t):
            parent = fk["referred_table"].upper()
            child = t.upper()
            cols = ",".join(fk["constrained_columns"])
            relations.append(f'    {parent} ||--o{{ {child} : "{cols}"')
        # Block
        lines = [f"    {t.upper()} {{"]
        for col in insp.get_columns(t):
            flags = _column_flags(t, col, insp)
            tag = ""
            if flags["pk"]:
                tag = " PK"
            elif flags["fk"]:
                tag = " FK"
            elif flags["unique"]:
                tag = " UK"
            mtype = _mermaid_type(str(col["type"]))
            lines.append(f"        {mtype:<8} {col['name']}{tag}")
        lines.append("    }")
        blocks.append("\n".join(lines))
    return "erDiagram\n" + "\n".join(relations) + "\n\n" + "\n\n".join(blocks)


# ---- Per-table card

def render_table_card(t: str, insp: Inspector) -> str:
    cols = insp.get_columns(t)
    label = TABLE_LABELS.get(t, "")
    rows_html: list[str] = []
    for col in cols:
        name = col["name"]
        flags = _column_flags(t, col, insp)
        badge_html: list[str] = []
        if flags["pk"]:
            badge_html.append('<span class="badge pk">PK</span>')
        if flags["fk"]:
            badge_html.append('<span class="badge fk">FK</span>')
        if flags["unique"] and not flags["pk"]:
            badge_html.append('<span class="badge uq">UQ</span>')
        if flags["indexed"] and not flags["unique"]:
            badge_html.append('<span class="badge idx">IDX</span>')
        if flags["notnull"]:
            badge_html.append('<span class="badge notnull">NN</span>')
        if flags["nullable"]:
            badge_html.append('<span class="badge null">NULL</span>')
        note = COLUMN_NOTES.get((t, name), "")
        fk_note = _fk_target(t, name, insp)
        if fk_note:
            note = f"{fk_note}" + (f"，{note}" if note else "")
        rows_html.append(
            "<tr>"
            f'<td class="col-name">{html.escape(name)}</td>'
            f'<td class="col-type">{html.escape(_normalize_type(str(col["type"])))}</td>'
            f'<td class="col-flags">{"".join(badge_html)}</td>'
            f'<td class="col-note">{note}</td>'
            "</tr>"
        )
    notes_html = ""
    if t in TABLE_NOTES:
        notes_html = f'<div class="notes">{TABLE_NOTES[t]}</div>'
    return f"""\
<details data-table="{html.escape(t)}">
<summary>
  <svg class="caret" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="5,3 11,8 5,13"/></svg>
  <span class="table-name">{html.escape(t)}</span>
  <span class="table-tag">{len(cols)} columns{f" · {html.escape(label)}" if label else ""}</span>
</summary>
<div class="fields">
<table>
  <thead><tr><th>欄位</th><th>型別</th><th>約束</th><th>說明</th></tr></thead>
  <tbody>
    {"".join(rows_html)}
  </tbody>
</table>
</div>
{notes_html}
</details>"""


# ---- Top-level page

CSS = """\
:root {
  --bg: #FAFAF9; --card: #FFFFFF; --border: #E7E5E4; --border-strong: #D6D3D1;
  --text: #1C1917; --text-soft: #57534E; --text-muted: #A8A29E;
  --primary: #475569; --primary-dark: #334155;
  --accent: #0EA5E9; --accent-soft: #E0F2FE;
  --head-bg: #F5F5F4;
  --pk: #B45309; --pk-soft: #FEF3C7;
  --fk: #1D4ED8; --fk-soft: #DBEAFE;
  --uq: #7C3AED; --uq-soft: #EDE9FE;
  --idx: #047857; --idx-soft: #D1FAE5;
  --null: #6B7280; --null-soft: #F3F4F6;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, Inter, "Segoe UI", "PingFang TC", "Noto Sans TC", "Microsoft JhengHei", sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.55; font-size: 14px;
  padding: 32px 24px 64px; -webkit-font-smoothing: antialiased;
}
.wrap { max-width: 1080px; margin: 0 auto; }
header { margin-bottom: 28px; }
h1 { font-size: 24px; font-weight: 600; letter-spacing: -0.015em; margin-bottom: 4px; }
.subtitle { color: var(--text-muted); font-size: 13px; letter-spacing: 0.02em; }
.section-title {
  font-size: 12px; font-weight: 500; color: var(--text-muted);
  letter-spacing: 0.08em; text-transform: uppercase; margin: 32px 0 12px;
}
.card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }

.er-card { padding: 20px; overflow-x: auto; }
.mermaid { font-family: inherit; min-width: 600px; }

.toolbar { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.btn {
  background: var(--card); border: 1px solid var(--border-strong); color: var(--text);
  padding: 6px 12px; border-radius: 8px; font: inherit; font-size: 12px;
  cursor: pointer; transition: all 0.12s ease;
}
.btn:hover { border-color: var(--text-soft); background: #FCFCFB; }
.filter-input {
  flex: 1; min-width: 180px; background: var(--card); border: 1px solid var(--border-strong);
  color: var(--text); padding: 6px 12px; border-radius: 8px; font: inherit; font-size: 13px;
}
.filter-input:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }

details {
  background: var(--card); border: 1px solid var(--border); border-radius: 12px;
  margin-bottom: 10px; overflow: hidden; transition: border-color 0.12s ease;
}
details[open] { border-color: var(--border-strong); }
summary {
  list-style: none; cursor: pointer; padding: 14px 18px;
  display: flex; align-items: center; gap: 12px; font-weight: 600; user-select: none;
  transition: background 0.12s ease;
}
summary::-webkit-details-marker { display: none; }
summary:hover { background: rgba(28,25,23,0.025); }
.caret { width: 14px; height: 14px; display: inline-block; transition: transform 0.15s ease; color: var(--text-muted); flex-shrink: 0; }
details[open] .caret { transform: rotate(90deg); }
.table-name { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 14px; color: var(--text); }
.table-tag { margin-left: auto; font-size: 11px; color: var(--text-muted); font-weight: 500; letter-spacing: 0.02em; }

.fields { border-top: 1px solid var(--border); overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
thead { background: var(--head-bg); }
thead th {
  text-align: left; font-size: 11px; font-weight: 600; color: var(--text-soft);
  letter-spacing: 0.04em; text-transform: uppercase; padding: 10px 16px;
  border-bottom: 1px solid var(--border); white-space: nowrap;
}
tbody td { padding: 10px 16px; border-bottom: 1px solid var(--border); vertical-align: top; font-size: 13px; }
tbody tr:last-child td { border-bottom: none; }
tbody tr:hover { background: rgba(28,25,23,0.02); }
td.col-name { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-weight: 600; color: var(--text); white-space: nowrap; }
td.col-type { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; color: var(--text-soft); font-size: 12.5px; white-space: nowrap; }
td.col-flags { white-space: nowrap; }
td.col-note { color: var(--text-soft); }

.badge {
  display: inline-block; font-size: 10px; font-weight: 600;
  padding: 2px 6px; border-radius: 4px; margin-right: 4px;
  letter-spacing: 0.04em; text-transform: uppercase; line-height: 1.4;
}
.badge.pk { background: var(--pk-soft); color: var(--pk); }
.badge.fk { background: var(--fk-soft); color: var(--fk); }
.badge.uq { background: var(--uq-soft); color: var(--uq); }
.badge.idx { background: var(--idx-soft); color: var(--idx); }
.badge.null { background: var(--null-soft); color: var(--null); }
.badge.notnull { background: #FEE2E2; color: #991B1B; }

.notes { padding: 12px 18px 16px; border-top: 1px solid var(--border); background: #FCFCFB; font-size: 13px; color: var(--text-soft); }
.notes b { color: var(--text); font-weight: 600; }
.notes ul { margin-left: 18px; margin-top: 4px; }
.notes li { margin-bottom: 2px; }
.notes code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; background: #F5F5F4; padding: 1px 4px; border-radius: 3px; font-size: 12px; }

.hidden { display: none !important; }
footer { margin-top: 40px; color: var(--text-muted); font-size: 12px; text-align: center; }
footer code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
"""


def render_page(engine: Engine) -> str:
    insp = inspect(engine)
    # Use TABLE_ORDER for display, but include any extra reflected tables at the end.
    db_tables = [
        t for t in insp.get_table_names() if t != "alembic_version"
    ]
    ordered = [t for t in TABLE_ORDER if t in db_tables]
    extras = sorted(t for t in db_tables if t not in TABLE_ORDER)
    tables = ordered + extras

    # Current alembic revision (best-effort).
    rev = "?"
    try:
        with engine.connect() as conn:
            row = conn.exec_driver_sql("SELECT version_num FROM alembic_version").fetchone()
            if row:
                rev = row[0]
    except Exception:
        pass

    mermaid_src = render_mermaid(engine, insp)
    cards = "\n".join(render_table_card(t, insp) for t in tables)
    today = _dt.date.today().isoformat()
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>my_sales_system — DB Schema</title>
<style>
{CSS}
</style>
</head>
<body>
<div class="wrap">

<header>
  <h1>my_sales_system — Database Schema</h1>
  <div class="subtitle">{len(tables)} tables · generated {today} · alembic rev <code>{html.escape(rev)}</code></div>
</header>

<div class="section-title">ER Diagram</div>
<div class="card er-card">
<pre class="mermaid">
{html.escape(mermaid_src)}
</pre>
</div>

<div class="section-title">Tables</div>

<div class="toolbar">
  <input class="filter-input" id="filter" type="search" placeholder="搜尋表名 / 欄位名…" />
  <button class="btn" onclick="setAll(true)">全部展開</button>
  <button class="btn" onclick="setAll(false)">全部收合</button>
</div>

{cards}

<footer>
  Source of truth: <code>backend/app/models/*.py</code> · 由 <code>python -m app.scripts.dump_schema_html</code> 自動產生
</footer>

</div>

<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  mermaid.initialize({{
    startOnLoad: true,
    theme: 'base',
    themeVariables: {{
      fontFamily: '-apple-system, BlinkMacSystemFont, Inter, "Segoe UI", "PingFang TC", "Noto Sans TC", sans-serif',
      fontSize: '13px',
      primaryColor: '#FFFFFF',
      primaryBorderColor: '#475569',
      primaryTextColor: '#1C1917',
      lineColor: '#78716C',
      tertiaryColor: '#FAFAF9',
    }},
  }});
</script>

<script>
  function setAll(open) {{
    document.querySelectorAll('details[data-table]').forEach(d => {{ d.open = open }});
  }}
  const filter = document.getElementById('filter');
  filter.addEventListener('input', () => {{
    const q = filter.value.trim().toLowerCase();
    document.querySelectorAll('details[data-table]').forEach(d => {{
      if (!q) {{ d.classList.remove('hidden'); return; }}
      const tableName = d.dataset.table.toLowerCase();
      const cols = [...d.querySelectorAll('td.col-name')].map(td => td.textContent.toLowerCase());
      const hit = tableName.includes(q) || cols.some(c => c.includes(q));
      d.classList.toggle('hidden', !hit);
      if (hit && !tableName.includes(q)) d.open = true;
    }});
  }});
</script>

</body>
</html>
"""


def main() -> None:
    default = Path(__file__).resolve().parents[3] / "docs" / "database" / "schema.html"
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else default
    out.parent.mkdir(parents=True, exist_ok=True)
    html_text = render_page(engine)
    out.write_text(html_text, encoding="utf-8")
    print(f"Wrote {out}  ({len(html_text):,} bytes)")


if __name__ == "__main__":
    main()
