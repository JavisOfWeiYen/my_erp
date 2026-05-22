"""my_erp seed CLI.

Generates an 18-month story-driven dataset (2024-12 ~ 2026-05) against a
running backend instance. See seed/PLAN.html for the full story.

Current state: Step 3 lands the "static" generators (setup + people +
catalog). Steps 4-5 (timeline + scripted events) still print as stubs.
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
    run_people,
    run_setup,
    run_timeline,
)


# Each tuple: (step_name, description, runs_at_step_3?). Step 4-5 keep
# their slots so --stop-after / --help stays accurate.
STEPS: list[tuple[str, str]] = [
    ("setup", "Verify backend reachable + log in as admin"),
    ("people", "Create 50 staff (admin 2 + manager 6 + sales 28 + warehouse 14)"),
    ("catalog", "Create 6 suppliers + 5 categories + 37 products + 30 customers"),
    ("timeline", "18-month PO/receive/SO/confirm loop + raw-SQL timestamp backdate"),
    ("events", "Scripted events: price hikes, churn, stockouts, adjustments, payments, voids"),
]

IMPLEMENTED_STEPS = {"setup", "people", "catalog", "timeline"}


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
        help="Wipe existing seed-generated rows before running (not yet implemented).",
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
    if args.reset:
        print("[seed] --reset is not implemented yet; aborting.", file=sys.stderr)
        return 2
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

        run_timeline(client, state)
        if stop_after == "timeline":
            print("[seed] stopped after 'timeline'.")
            return 0

        if stop_after in (None, "events"):
            print("[seed] 'events' step not implemented yet — done.")

    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cfg = load_config()
    print_plan(args, cfg)

    if args.dry_run:
        print("[dry-run] No backend or DB calls made. Exiting.")
        return 0

    return execute(args, cfg)


if __name__ == "__main__":
    sys.exit(main())
