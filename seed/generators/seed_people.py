"""People generator: 50 users + 50 employees.

For each PersonConfig we POST /users first (capturing the assigned user_id)
then POST /employees with the matching ``user_id`` and ``initial_salary`` —
the employees endpoint auto-creates the first salary_record (reason=hire).

Idempotent: existing users are matched by username, existing employees by
``user_id``. Re-running adopts both without writing duplicate salary records.
"""
from __future__ import annotations

from typing import Any

from seed.config import people as people_cfg

from ._payload import build_payload
from .api_client import SeedAPIClient
from .seed_setup import SeedState


def _index_users_by_username(client: SeedAPIClient) -> dict[str, int]:
    rows = client.get("/users", params={"limit": 200}).json()
    return {row["username"]: row["id"] for row in rows}


def _index_employees_by_user_id(client: SeedAPIClient) -> dict[int, int]:
    rows = client.get(
        "/employees", params={"limit": 200, "include_terminated": True}
    ).json()
    return {row["user"]["id"]: row["id"] for row in rows if row.get("user")}


def _user_payload(person: dict[str, Any], role_ids: dict[str, int]) -> dict[str, Any]:
    return {
        "username": person["username"],
        "email": person["email"],
        "full_name": person["full_name"],
        "password": people_cfg.DEFAULT_PASSWORD,
        "role_id": role_ids[person["role_name"]],
        "is_active": True,
    }


def _employee_payload(person: dict[str, Any], user_id: int) -> dict[str, Any]:
    payload = build_payload(
        person,
        drop={
            "code", "username", "full_name", "email", "role_name",
            "tier",  # sales-only seed metadata
        },
    )
    payload["user_id"] = user_id
    return payload


def seed_users(client: SeedAPIClient, state: SeedState) -> None:
    print(f"[people] users ({len(people_cfg.PEOPLE)} total) ...")
    existing = _index_users_by_username(client)
    created = adopted = 0
    for person in people_cfg.PEOPLE:
        if person["username"] in existing:
            state.user_ids[person["code"]] = existing[person["username"]]
            adopted += 1
            continue
        payload = _user_payload(person, state.role_ids)
        resp = client.post("/users", json=payload)
        state.user_ids[person["code"]] = resp.json()["id"]
        created += 1
    print(f"[people]   users: {created} created, {adopted} adopted")


def seed_employees(client: SeedAPIClient, state: SeedState) -> None:
    print(f"[people] employees ({len(people_cfg.PEOPLE)} total) ...")
    existing = _index_employees_by_user_id(client)
    created = adopted = 0
    for person in people_cfg.PEOPLE:
        user_id = state.user_ids[person["code"]]
        if user_id in existing:
            state.employee_ids[person["code"]] = existing[user_id]
            adopted += 1
            continue
        payload = _employee_payload(person, user_id)
        resp = client.post("/employees", json=payload)
        state.employee_ids[person["code"]] = resp.json()["id"]
        created += 1
    print(f"[people]   employees: {created} created, {adopted} adopted")


def run_people(client: SeedAPIClient, state: SeedState) -> None:
    """Create users then employees, keyed by PersonConfig.code."""
    seed_users(client, state)
    seed_employees(client, state)
