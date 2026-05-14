# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`my_sales_system` is a sales / inventory (進銷存) management system, built from scratch.

- **Backend**: Python + FastAPI + SQLAlchemy + Alembic in `backend/`
- **Frontend**: Vite + React + Material-UI + react-i18next in `frontend/`
- **Database**: SQLite by default, swappable to PostgreSQL / MySQL via `DATABASE_URL`
- **Auth**: JWT + multi-role RBAC (4 roles: `admin`, `manager`, `sales`, `warehouse`). bcrypt direct (not passlib — see "Conventions").

The user prefers **Traditional Chinese (繁體中文)** for conversation and explanations; code, comments, and commits stay in English.

## MVP scope (in build order)

1. ✅ Phase 0 — backend & frontend skeletons
2. ✅ Phase 1 — User / Role + JWT auth (`/api/v1/auth/login`, `/auth/me`, `/users` admin-only CRUD, `/roles`; frontend AuthContext + ProtectedRoute + LoginPage + UsersPage with role/active filter, create/edit/delete, password edit treated as optional reset, self-delete blocked in UI)
3. ✅ Phase 2 — Products + Categories (`/products`, `/categories` CRUD; admin+manager write, all roles read; `stock_quantity` is read-only via this API and only mutated by purchase/sale flows; ProductsPage + CategoriesPage with search/filter/RBAC-gated actions)
4. ✅ Phase 3 — Purchase Orders + Suppliers (`/suppliers` CRUD; `/purchase-orders` two-stage flow — `POST` creates a `draft`, `POST /{id}/receive` flips to `received` + adds stock + writes back `product.cost_price`, `POST /{id}/cancel` flips to `cancelled`; only drafts are editable. `po_number` auto-generated as `PO-YYYYMMDD-####`. RBAC: admin+manager create/edit/cancel; admin+manager+warehouse receive; all roles read. SuppliersPage + PurchasesPage with dynamic line-items editor. Tables: `purchase_orders` + `purchase_order_items`.)
5. ✅ Phase 4 — Sales Orders + Customers (`/customers` CRUD; `/sales-orders` two-stage flow — `POST` creates a `draft` (no stock check), `POST /{id}/confirm` validates `stock_quantity ≥ quantity` per product and atomically decrements stock + sets `confirmed_at`, `POST /{id}/cancel` flips to `cancelled` (drafts only). `unit_price` is NOT written back to `product.unit_price` (the product owns its list price). `so_number` auto-generated as `SO-YYYYMMDD-####`. RBAC: admin+manager+sales for all writes; all roles read. CustomersPage + SalesPage; sale editor auto-fills unit_price from product and warns when qty exceeds on-hand. Tables: `sales_orders` + `sales_order_items`. **Salesperson attribution**: `sales_orders.salesperson_id` (NOT NULL FK → users) is separate from `created_by_id` so a manager can key an order on behalf of a rep; filterable on list and exposed in create/edit/detail. Lightweight `GET /users/staff` endpoint (any authenticated user) feeds the salesperson selector.
6. ✅ Phase 5 — Inventory queries & reports (Product gains `low_stock_threshold: int default 0`; threshold 0 disables the alert. `/inventory/stock` lists current on-hand with `is_low` computed; supports `search`/`category_id`/`low_only`/`include_inactive`. `/inventory/monthly-report?year=&month=` returns per-product opening/qty_in/qty_out/closing/purchase_amount/sales_amount — closing rolled back from current stock by subtracting net moves after month-end, so the same row stays consistent for past, current, and future months. Only received purchases and confirmed sales count. `/inventory/monthly-report.xlsx` streams an openpyxl workbook with a styled header row, totals row, and Chinese column titles. All endpoints are authenticated, no extra RBAC. Frontend: InventoryPage with low-only toggle and warning-tinted rows; ReportsPage with year/month selectors, totals strip, and "匯出 Excel" download.)

**Seeding** (one-time, idempotent): `python -m app.scripts.seed` creates the 4 roles and an initial admin user from `INITIAL_ADMIN_*` env vars. Default admin is `admin` / `ChangeMe!2026` — the user may have changed it.

## Common commands

### Backend (from `backend/`)

```bash
# First-time setup (WSL needs python3.12-venv installed: sudo apt install -y python3.12-venv)
python3 -m venv venv
source venv/bin/activate                # Windows PowerShell: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# Run dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Migrations
alembic revision --autogenerate -m "describe change"
alembic upgrade head
alembic downgrade -1

# Seed roles + initial admin (idempotent)
python -m app.scripts.seed
```

API docs at `/docs`, health checks at `/api/v1/health` and `/api/v1/health/db`.

### Frontend (from `frontend/`)

```bash
npm install
cp .env.example .env
npm run dev          # http://localhost:5173
npm run build        # production build
npm run lint
```

## Architecture

### Backend layout

```
backend/app/
├── main.py              FastAPI factory + CORS + router mounting
├── core/
│   ├── config.py        pydantic-settings, reads .env
│   ├── database.py      SQLAlchemy engine + SessionLocal + Base + get_db dep
│   ├── security.py      bcrypt direct (hash_password, verify_password) + JWT encode/decode
│   └── deps.py          DbDep, TokenDep, CurrentUser, get_current_user, require_roles(*roles)
├── models/              SQLAlchemy ORM models — all must be imported in models/__init__.py for Alembic autogenerate
├── schemas/             Pydantic request/response schemas
├── crud/                DB operations (kept thin)
├── scripts/seed.py      Idempotent seeding of roles + initial admin
└── api/v1/
    ├── router.py        Aggregates all v1 routers under /api/v1
    └── endpoints/       Per-resource routers (health, auth, users, roles, ...)
```

**RBAC pattern**: for admin-only endpoints, use `_: User = Depends(require_roles("admin"))` as a parameter — **not** `_: CurrentUser = Depends(...)`, because FastAPI rejects combining `Annotated[..., Depends()]` with a `= Depends()` default. The `CurrentUser` alias works for parameters *without* an additional `Depends(...)` default.

**Database-agnostic rules** (enforced because user wants to swap DBs):
- All DB access via SQLAlchemy ORM — no SQLite-specific raw SQL, no `AUTOINCREMENT` literals, no SQLite-only functions.
- `core/database.py:_build_engine_kwargs` returns SQLite-specific options (`check_same_thread=False`) only for SQLite URLs; other engines get `pool_pre_ping=True`.
- Alembic uses `render_as_batch=True` for SQLite (required for ALTER TABLE), off for others — already wired in `alembic/env.py`.

### Frontend layout

```
frontend/src/
├── main.jsx           Providers: ThemeProvider → CssBaseline → BrowserRouter → App, plus i18n init
├── App.jsx            Route table; uses <Layout/> as the parent route
├── theme.js           MUI theme — includes Chinese font stack (Noto Sans TC / PingFang TC / Microsoft JhengHei)
├── i18n.js            react-i18next with localStorage detection, default zh-TW
├── api/
│   ├── client.js      Axios instance — auto-attaches Bearer token, clears it on 401
│   └── auth.js        login (form-encoded), getCurrentUser
├── contexts/AuthContext.jsx   useAuth() → { user, login, logout, hasRole, isAuthenticated, loading }
├── locales/{zh-TW,en}.json
├── components/
│   ├── Layout.jsx         Drawer + AppBar shell w/ language switcher + user menu + role-filtered nav
│   └── ProtectedRoute.jsx Wraps routes; redirects unauthenticated → /login; supports roles=[...] for RBAC
└── pages/             LoginPage, HomePage, NotFoundPage, PlaceholderPage, ...
```

- Path alias `@/` → `src/` (see `vite.config.js`).
- Language switching lives in the AppBar; persists via localStorage.
- Auth token in `localStorage.access_token`. `AuthContext` auto-fetches `/auth/me` on token presence; failure clears the token.
- Use `<ProtectedRoute roles={['admin']}>` to gate routes by role; nav items also filter via `hasRole(...)`.

## Conventions

- **Never write SQLite-specific SQL** — the user explicitly chose a swappable DB design. Use SQLAlchemy ORM constructs; if raw SQL is unavoidable, use `text()` with portable syntax.
- **Schema changes go through Alembic** — never modify the DB directly or rely on `Base.metadata.create_all`.
- **Add new models to `app/models/__init__.py`** so Alembic autogenerate picks them up.
- **Password hashing: bcrypt direct, NOT passlib.** `passlib==1.7.4` breaks against `bcrypt>=4.1` (`AttributeError: module 'bcrypt' has no attribute '__about__'`). The project uses `bcrypt` directly in `core/security.py` with a 72-byte truncation helper. Do not re-add passlib.
- **UI strings go through i18n** — add keys to both `zh-TW.json` and `en.json`, never hardcode user-visible text in components.
- **Don't put secrets in `.env.example`** — keep real values in untracked `.env`.

## Environment notes

- Codebase lives on Windows mount (`/mnt/c/...`) accessed via WSL. The user may also run the backend natively in Windows PowerShell.
- WSL Ubuntu requires `sudo apt install -y python3.12-venv` before `python3 -m venv` works.
- `uvicorn --reload` on a Windows mount can briefly hang after a large batch of file writes (watchfiles flakiness). Give it 2-3s; if curl still hangs, sanity-check imports via `./venv/bin/python -c "from app.main import app; print(len(app.routes))"` before suspecting code.
- When user has their own uvicorn running in their terminal, **don't kill it** — ask them to restart, since they own the process.
