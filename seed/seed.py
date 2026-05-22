"""my_erp seed CLI.

Generates an 18-month story-driven dataset (2024-12 ~ 2026-05) against a
running backend instance. See seed/PLAN.html for the story design and
seed/STORYLINES.md for what every scripted scenario produces.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# When invoked as `python seed/seed.py`, the script's directory (`seed/`) is
# on sys.path but the project root is not. Add the project root so the
# `seed.*` package imports resolve consistently with `python -m seed.seed`.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

from seed.generators import (  # noqa: E402
    SeedAPIClient,
    SeedState,
    run_catalog,
    run_events,
    run_finalize,
    run_people,
    run_reset,
    run_setup,
    run_timeline,
)


STEPS: list[tuple[str, str]] = [
    ("setup", "Verify backend reachable + log in as admin"),
    ("people", "Create 50 staff (admin 2 + manager 6 + sales 28 + warehouse 14)"),
    ("catalog", "Create 6 suppliers + 5 categories + 37 products + 30 customers"),
    ("timeline", "18-month PO/receive/SO/confirm loop + raw-SQL timestamp backdate"),
    ("events", "Scripted events: stock adjustments / AR/AP payments / voids"),
    ("finalize", "Rewrite *_number prefixes from backdated dates"),
]

IMPLEMENTED_STEPS = {"setup", "people", "catalog", "timeline", "events", "finalize"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="seed.py",
        description="my_erp story-driven seed generator.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan without contacting the backend or DB.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Wipe PO/SO/AR/AP/payments/adjustments and reset stock/cost_price "
             "to baseline before running the timeline step.",
    )
    parser.add_argument(
        "--stop-after",
        choices=[name for name, _ in STEPS],
        help="Stop after the named step instead of running the whole pipeline.",
    )
    return parser.parse_args(argv)


def load_config() -> dict[str, str]:
    """Load seed/.env (if present) and return the resolved settings.

    Resolves any relative SQLite path in SEED_DATABASE_URL against the
    ``seed/`` directory so the script works no matter what cwd it runs from.
    """
    seed_dir = Path(__file__).parent
    env_path = seed_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    raw_db_url = os.getenv("SEED_DATABASE_URL", "sqlite:///../backend/seed.db")
    db_url = raw_db_url
    if raw_db_url.startswith("sqlite:///") and not raw_db_url.startswith("sqlite:////"):
        # Three-slash form = relative path; resolve against seed/.
        rel = raw_db_url[len("sqlite:///"):]
        abs_path = (seed_dir / rel).resolve()
        db_url = f"sqlite:///{abs_path}"

    return {
        "api_base_url": os.getenv("API_BASE_URL", "http://localhost:8000/api/v1"),
        "seed_database_url": db_url,
        "admin_username": os.getenv("SEED_ADMIN_USERNAME", "admin"),
        "admin_password": os.getenv("SEED_ADMIN_PASSWORD") or "",
    }


def print_plan(args: argparse.Namespace, cfg: dict[str, str]) -> None:
    bar = "=" * 64
    print(bar)
    print("my_erp seed plan")
    print(bar)
    print(f"  API base URL      : {cfg['api_base_url']}")
    print(f"  Seed database URL : {cfg['seed_database_url']}")
    print(f"  Admin username    : {cfg['admin_username']}")
    print(f"  Admin password    : {'yes' if cfg['admin_password'] else 'no (default)'}")
    print(f"  Mode              : {'DRY RUN' if args.dry_run else 'EXECUTE'}")
    print(f"  Stop after        : {args.stop_after or '(run all)'}")
    print(f"  Reset first       : {'yes' if args.reset else 'no'}")
    print()
    print("Steps:")
    for idx, (name, desc) in enumerate(STEPS, start=1):
        mark = "✓" if name in IMPLEMENTED_STEPS else "·"
        print(f"  {mark} {idx}. {name:<8} — {desc}")
    print()


def execute(args: argparse.Namespace, cfg: dict[str, str]) -> int:
    if not cfg["admin_password"]:
        print(
            "[seed] SEED_ADMIN_PASSWORD is empty — set it in seed/.env.",
            file=sys.stderr,
        )
        return 2

    stop_after = args.stop_after
    with SeedAPIClient(cfg["api_base_url"], cfg["seed_database_url"]) as client:
        state = run_setup(
            client,
            username=cfg["admin_username"],
            password=cfg["admin_password"],
        )
        if stop_after == "setup":
            print("[seed] stopped after 'setup'.")
            return 0

        run_people(client, state)
        if stop_after == "people":
            print("[seed] stopped after 'people'.")
            return 0

        run_catalog(client, state)
        if stop_after == "catalog":
            print("[seed] stopped after 'catalog'.")
            return 0

        # --reset wipes transactional data after the catalogue is in place,
        # so the timeline below starts from a clean slate.
        if args.reset:
            run_reset(client)

        run_timeline(client, state)
        if stop_after == "timeline":
            print("[seed] stopped after 'timeline'.")
            return 0

        run_events(client, state)
        if stop_after == "events":
            print("[seed] stopped after 'events'.")
            return 0

        run_finalize(client)
        if stop_after == "finalize":
            print("[seed] stopped after 'finalize'.")
            return 0

    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cfg = load_config()
    print_plan(args, cfg)

    if args.dry_run:
        print("[dry-run] No backend or DB calls made. Exiting.")
        return 0

    try:
        return execute(args, cfg)
    except RuntimeError as exc:
        # Generators raise RuntimeError for expected user-facing failures
        # (e.g. timeline idempotency guard). Print the message, not the
        # traceback.
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
