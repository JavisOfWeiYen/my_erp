"""Setup generator: verify backend is reachable and log in as the admin.

This is the first generator run in seed.py — every later step depends on a
healthy backend + valid bearer token. We also pre-fetch the `/roles` table
since the people generator needs role_name → role_id mapping.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .api_client import SeedAPIClient, SeedAPIError


@dataclass
class SeedState:
    """Shared mutable state carried through every step.

    Step 3 populates the lookup tables (code → backend id). Step 4 will read
    them to drive PO/SO creation. Keep this serialisable — Step 6 will
    snapshot it to a JSON checkpoint between sessions.
    """
    role_ids: dict[str, int] = field(default_factory=dict)
    supplier_ids: dict[str, int] = field(default_factory=dict)
    category_ids: dict[str, int] = field(default_factory=dict)
    product_ids: dict[str, int] = field(default_factory=dict)
    customer_ids: dict[str, int] = field(default_factory=dict)
    user_ids: dict[str, int] = field(default_factory=dict)
    employee_ids: dict[str, int] = field(default_factory=dict)


def run_setup(client: SeedAPIClient, *, username: str, password: str) -> SeedState:
    """Health-check, log in, cache role ids. Returns a fresh SeedState."""
    print("[setup] pinging backend ...")
    health = client._http.get("/health")
    if health.status_code != 200:
        raise SeedAPIError("GET", "/health", health)

    db_health = client._http.get("/health/db")
    if db_health.status_code != 200:
        raise SeedAPIError("GET", "/health/db", db_health)

    print(f"[setup] logging in as {username!r} ...")
    client.login(username, password)

    me = client.get("/auth/me").json()
    if me.get("role", {}).get("name") != "admin":
        raise RuntimeError(
            f"seed admin {username!r} must be in the 'admin' role; got {me.get('role')}"
        )

    state = SeedState()
    roles = client.get("/roles").json()
    for role in roles:
        state.role_ids[role["name"]] = role["id"]
    for required in ("admin", "manager", "sales", "warehouse"):
        if required not in state.role_ids:
            raise RuntimeError(
                f"role {required!r} missing in seed DB; "
                "run `python -m app.scripts.seed` against seed.db first"
            )
    print(f"[setup] roles: {state.role_ids}")
    return state
