import os
import tempfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent

# Point pydantic-settings at a temp SQLite file BEFORE importing app modules.
_db_fd, _DB_PATH = tempfile.mkstemp(suffix=".db", prefix="my_sales_test_")
os.close(_db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, SessionLocal  # noqa: E402
from app.crud import role as role_crud  # noqa: E402
from app.crud import user as user_crud  # noqa: E402
from app.main import app  # noqa: E402
from app.schemas.user import UserCreate  # noqa: E402

ROLES = [
    ("admin", "Administrator"),
    ("manager", "Manager"),
    ("sales", "Sales staff"),
    ("warehouse", "Warehouse staff"),
]
TEST_PASSWORD = "testpass123"


@pytest.fixture(scope="session", autouse=True)
def _migrate_schema():
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.upgrade(cfg, "head")
    yield
    try:
        os.unlink(_DB_PATH)
    except OSError:
        pass


def _truncate_all(db):
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()


@pytest.fixture
def db_session():
    s = SessionLocal()
    try:
        _truncate_all(s)
        yield s
    finally:
        s.close()


@pytest.fixture
def roles(db_session):
    for name, desc in ROLES:
        role_crud.create(db_session, name=name, description=desc)
    return {r.name: r for r in role_crud.list_all(db_session)}


@pytest.fixture
def users(db_session, roles):
    out = {}
    for role_name in roles:
        out[role_name] = user_crud.create(
            db_session,
            UserCreate(
                username=role_name,
                email=f"{role_name}@example.com",
                full_name=role_name.capitalize(),
                password=TEST_PASSWORD,
                role_id=roles[role_name].id,
                is_active=True,
            ),
        )
    return out


@pytest.fixture
def client(users):
    with TestClient(app) as c:
        yield c


def _login(client: TestClient, username: str) -> str:
    r = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": TEST_PASSWORD},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture
def auth(client):
    """Return a callable that yields an authenticated TestClient for the given role."""
    def _make(role: str) -> TestClient:
        token = _login(client, role)
        c = TestClient(app)
        c.headers["Authorization"] = f"Bearer {token}"
        return c
    return _make
