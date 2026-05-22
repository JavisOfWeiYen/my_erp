"""HTTP + DB client for seed scripts.

The backend owns business logic (stock decrement, AR/AP creation, cost
snapshots), so we write through its API. Server-set timestamps
(`confirmed_at`, `received_at`, `paid_at`) cannot be backdated through the API
— a separate SQLAlchemy engine performs raw UPDATEs against the same database
to push records to historical dates.
"""
from __future__ import annotations

from typing import Any

import httpx
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


class SeedAPIError(RuntimeError):
    """Raised when the backend returns a non-2xx status."""

    def __init__(self, method: str, path: str, response: httpx.Response) -> None:
        try:
            detail: Any = response.json()
        except ValueError:
            detail = response.text
        super().__init__(
            f"{method} {path} → HTTP {response.status_code}: {detail!r}"
        )
        self.method = method
        self.path = path
        self.status_code = response.status_code
        self.detail = detail


class SeedAPIClient:
    """Authenticated HTTP session plus a SQLAlchemy engine for backdating.

    Lifecycle: construct → login() → operate → close().
    """

    def __init__(self, base_url: str, db_url: str, *, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.db_url = db_url
        self._http: httpx.Client = httpx.Client(base_url=self.base_url, timeout=timeout)
        self._engine: Engine = create_engine(db_url, future=True)
        self._token: str | None = None

    @property
    def authenticated(self) -> bool:
        return self._token is not None

    @property
    def engine(self) -> Engine:
        return self._engine

    def login(self, username: str, password: str) -> None:
        """POST /auth/login (form-encoded) and store the bearer token."""
        # /auth/login uses OAuth2PasswordRequestForm — must be form-encoded.
        resp = self._http.post(
            "/auth/login",
            data={"username": username, "password": password},
        )
        if resp.status_code != 200:
            raise SeedAPIError("POST", "/auth/login", resp)
        self._token = resp.json()["access_token"]

    def request(
        self,
        method: str,
        path: str,
        *,
        expect: tuple[int, ...] = (200, 201, 204),
        ok_conflict: bool = False,
        **kwargs: Any,
    ) -> httpx.Response:
        """Issue an authenticated request and validate the status code.

        `expect` is the tuple of status codes treated as success. `ok_conflict`
        additionally treats 409 as success — callers use it for idempotent
        create-or-skip flows (catch 409 to mean "already exists, look it up").
        """
        if not self._token:
            raise RuntimeError("login() must be called before request()")
        headers = kwargs.pop("headers", {}) or {}
        headers.setdefault("Authorization", f"Bearer {self._token}")
        resp = self._http.request(method, path, headers=headers, **kwargs)
        allowed = set(expect)
        if ok_conflict:
            allowed.add(409)
        if resp.status_code not in allowed:
            raise SeedAPIError(method, path, resp)
        return resp

    def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.request("DELETE", path, **kwargs)

    def backdate(self, table: str, row_id: int, **values: Any) -> None:
        """Raw SQL UPDATE to push server-set timestamps into the past.

        Used by the timeline generator after POST /receive or /confirm to
        rewrite ``received_at`` / ``confirmed_at`` / AR.issued_at / AR.due_date
        etc. — fields whose backend logic sets them to ``now()``.

        Example:
            client.backdate("sales_orders", so_id, confirmed_at=dt, created_at=dt)
        """
        if not values:
            return
        # Build a parameterised statement; identifiers (table/column) are
        # whitelisted by being values from our own code, never user input.
        from sqlalchemy import text

        set_clause = ", ".join(f"{col} = :{col}" for col in values)
        stmt = text(f"UPDATE {table} SET {set_clause} WHERE id = :_row_id")
        with self._engine.begin() as conn:
            conn.execute(stmt, {**values, "_row_id": row_id})

    def backdate_where(self, table: str, where_col: str, where_val: Any, **values: Any) -> None:
        """Same as backdate() but match on an arbitrary column (e.g. AR.sales_order_id)."""
        if not values:
            return
        from sqlalchemy import text

        set_clause = ", ".join(f"{col} = :{col}" for col in values)
        stmt = text(
            f"UPDATE {table} SET {set_clause} WHERE {where_col} = :_where_val"
        )
        with self._engine.begin() as conn:
            conn.execute(stmt, {**values, "_where_val": where_val})

    def close(self) -> None:
        self._http.close()
        self._engine.dispose()

    def __enter__(self) -> "SeedAPIClient":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()
