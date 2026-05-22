"""Tiny helpers for shaping config dicts into JSON-safe API payloads."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable


def to_jsonable(value: Any) -> Any:
    """Convert seed-config values (Decimal, date) to JSON-encodable forms.

    The backend's Pydantic schemas accept ``str`` for both Decimal and
    date fields, so this just normalises and lets the server parse.
    """
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def build_payload(config: dict[str, Any], *, drop: Iterable[str] = ()) -> dict[str, Any]:
    """Strip seed-only fields and convert remaining values for JSON transport."""
    drop_set = set(drop)
    return {
        k: to_jsonable(v)
        for k, v in config.items()
        if k not in drop_set and v is not None
    }
