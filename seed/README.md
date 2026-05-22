# my_erp seed generator

Builds an 18-month story-driven dataset (2024-12 ~ 2026-05) for AI agent
analytics demos. The generator runs against a live backend and writes
into a dedicated `seed.db` so it never touches your dev database.

After a full run the database contains:

- 6 OEM suppliers (NVIDIA / AMD / Intel / Super Micro / Dell / HPE)
- 5 product categories + 37 SKUs
- 30 customers (11 scripted archetypes + 19 background filler)
- 50 staff (3 stars / 12 mid / 9 average / 3 declining / 1 newbie)
- ~97 POs / ~1576 SOs / 1551 AR payments / 97 AP payments
- 6 stock adjustments / 2 payment voids
- 32 scripted storylines verified in [`STORYLINES.md`](STORYLINES.md)

## Quick start

```bash
# 1. Build a clean seed.db (one-time, from project root)
cd backend
DATABASE_URL="sqlite:///./seed.db" ./venv/bin/alembic upgrade head
DATABASE_URL="sqlite:///./seed.db" ./venv/bin/python -m app.scripts.seed

# 2. Configure seed/.env (one-time)
cd ../seed
cp .env.example .env
# edit .env if the bootstrap admin password is not the default

# 3. Start the backend pointing at seed.db (separate terminal)
cd ../backend
DATABASE_URL="sqlite:///./seed.db" ./venv/bin/uvicorn app.main:app --port 8000

# 4. Run the full pipeline
cd ..
./backend/venv/bin/python -m seed.seed
```

A full run takes ~10 minutes (mostly ~1500 SO confirmations via the API).

## CLI

```
python -m seed.seed [--dry-run] [--reset] [--stop-after STEP]
```

| Flag | Description |
|---|---|
| `--dry-run` | Print the plan and exit; no API or DB calls. |
| `--reset` | Wipe transactional data (PO/SO/AR/AP/payments/adjustments) and reset `product.stock_quantity` + `cost_price` to baseline before the timeline step. Required if you've already run the timeline. |
| `--stop-after STEP` | Stop after the named step. Valid: `setup`, `people`, `catalog`, `timeline`, `events`, `finalize`. |

## Pipeline

1. **setup** — health-check backend + log in as admin + cache role ids.
2. **people** — POST 50 users + 50 employees (idempotent: match by username).
3. **catalog** — POST 6 suppliers / 5 categories / 37 products / 30 customers
   (idempotent: match by name / SKU).
4. **timeline** — two-pass main loop:
   1. *Plan pass* (in memory): walk every customer × month and decide
      orders using `ROLE_PROFILES` + customer overrides + seasonal
      multipliers + salesperson tier weights + personal events.
   2. *Execute pass* (per month): one PO per supplier covering planned
      demand + 15% buffer (applies stockout severity to received qty);
      then create + confirm each SO sorted by ordered date. All
      timestamps backdated via raw SQL.
   Refuses to run if PO/SO already exist in the DB — use `--reset`.
5. **events** — apply scripted post-timeline events:
   - 6 stock adjustments (`STOCK_ADJUST_EVENTS`)
   - 1551 AR payments sampled from `PAYMENT_PROFILE_BY_ROLE` per customer
   - 97 AP payments (all paid 0-5 days early)
   - 2 AR payment voids (`PAYMENT_VOID_EVENTS`)
6. **finalize** — rewrite `so_number` / `po_number` / `ar_number` /
   `ap_number` / `adjustment_number` from backdated dates. The backend's
   serial generators always prefix `today`, which spoils the demo; this
   step fixes them. (Payment numbers `REC-*` and `PAY-*` already use
   `paid_at` server-side and don't need this fix-up.)

## Verifying a populated database

```bash
python -m seed.scripts.verify
```

Runs 11 read-only KPI checks (monthly coverage, Q4/Q1 seasonality,
2026 margin compression, top vs bottom sales spread, 大同 zero overdue,
AR aging d90+ population, 祥豐 churn, stock adjustments / payment voids
counts, role-margin ordering, serial-number backfill). Exits 0 on
full pass.

## File layout

```
seed/
├── README.md          (this file)
├── STORYLINES.md      32 scripted storylines + 7 cross-cutting demo questions
├── PLAN.html          Original story design
├── seed.py            CLI entry point
├── .env.example       Template config
├── requirements.txt   httpx + sqlalchemy + python-dotenv (all in backend venv already)
├── config/            Static catalogues (suppliers / products / customers / people / stories)
├── generators/        Pipeline steps (setup / people / catalog / timeline / events / finalize / reset)
└── scripts/
    └── verify.py      Acceptance KPI checker
```

## Resetting and re-running

The timeline + events steps are NOT idempotent — re-running them on top
of an existing dataset would double everything. The timeline step
refuses to start if PO/SO rows already exist; pass `--reset` to wipe
transactional data and start fresh.

```bash
# Full fresh run from a populated DB
python -m seed.seed --reset
```

The reset preserves all static rows (suppliers / categories / products /
customers / users / employees) because Step 2-3 re-adopt them
idempotently anyway.

## Connecting to a different backend instance

By default the seed targets `http://localhost:8000/api/v1` (set in
`.env`). To point at a different host:

```bash
API_BASE_URL=https://my-staging-api.example/api/v1 \
SEED_DATABASE_URL=sqlite:////absolute/path/to/seed.db \
python -m seed.seed
```

`SEED_DATABASE_URL` must point at the *same* database the backend is
serving — the script uses raw SQL to backdate timestamps that the API
cannot set.
