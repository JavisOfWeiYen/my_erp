"""Seed generators (Step 3+).

The catalog and people generators are idempotent — they list existing rows
and only POST what's missing. Higher-level steps (timeline, events) plug in
later by reading id-lookup tables off the shared ``SeedState``.
"""
from __future__ import annotations

from .api_client import SeedAPIClient, SeedAPIError
from .seed_catalog import run_catalog
from .seed_events import run_events
from .seed_people import run_people
from .seed_setup import SeedState, run_setup
from .seed_timeline import run_timeline

__all__ = [
    "SeedAPIClient",
    "SeedAPIError",
    "SeedState",
    "run_setup",
    "run_catalog",
    "run_people",
    "run_timeline",
    "run_events",
]
