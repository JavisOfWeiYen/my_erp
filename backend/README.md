# Backend — My Sales System

FastAPI + SQLAlchemy + Alembic backend for the sales / inventory system.

## Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## Run the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API root: http://localhost:8000/
- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health
- DB health check: http://localhost:8000/api/v1/health/db

## Database migrations (Alembic)

```bash
# Create a new migration after model changes
alembic revision --autogenerate -m "describe change"

# Apply migrations
alembic upgrade head

# Roll back one revision
alembic downgrade -1
```

## Switching databases

Edit `DATABASE_URL` in `.env`. The engine config auto-adjusts for SQLite.

| Database   | Example DATABASE_URL                                              | Extra driver  |
|------------|-------------------------------------------------------------------|---------------|
| SQLite     | `sqlite:///./sales_system.db`                                     | (built-in)    |
| PostgreSQL | `postgresql+psycopg://user:pass@localhost:5432/sales_system`      | `psycopg[binary]` |
| MySQL      | `mysql+pymysql://user:pass@localhost:3306/sales_system`           | `pymysql`     |

Add the driver to `requirements.txt` if you switch.

## Project layout

```
app/
├── main.py              FastAPI factory + middleware
├── core/
│   ├── config.py        Settings (pydantic-settings, reads .env)
│   └── database.py      SQLAlchemy engine / session / Base
├── models/              SQLAlchemy ORM models
├── schemas/             Pydantic request/response schemas
├── crud/                DB access helpers
└── api/v1/
    ├── router.py        Aggregates all v1 routers
    └── endpoints/       Per-resource routers
alembic/                 Migration scripts
```
