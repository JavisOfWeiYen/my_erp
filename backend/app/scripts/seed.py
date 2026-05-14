"""Seed roles and initial admin user. Idempotent — safe to run multiple times.

Usage:
    python -m app.scripts.seed
"""
from app.core.config import settings
from app.core.database import SessionLocal
from app.crud import role as role_crud
from app.crud import user as user_crud
from app.schemas.user import UserCreate

DEFAULT_ROLES = [
    ("admin", "系統管理員 / Administrator (full access)"),
    ("manager", "主管 / Manager"),
    ("sales", "業務 / Sales staff"),
    ("warehouse", "倉管 / Warehouse staff"),
]


def seed() -> None:
    db = SessionLocal()
    try:
        created_roles = []
        for name, description in DEFAULT_ROLES:
            if not role_crud.get_by_name(db, name):
                role_crud.create(db, name=name, description=description)
                created_roles.append(name)
        print(f"Roles created: {created_roles or 'none (already exist)'}")

        admin_role = role_crud.get_by_name(db, "admin")
        if not admin_role:
            raise RuntimeError("admin role missing after seeding")

        existing = user_crud.get_by_username(db, settings.INITIAL_ADMIN_USERNAME)
        if existing:
            print(f"Admin user '{settings.INITIAL_ADMIN_USERNAME}' already exists.")
            return

        user_crud.create(
            db,
            UserCreate(
                username=settings.INITIAL_ADMIN_USERNAME,
                email=settings.INITIAL_ADMIN_EMAIL,
                full_name=settings.INITIAL_ADMIN_FULL_NAME,
                password=settings.INITIAL_ADMIN_PASSWORD,
                role_id=admin_role.id,
                is_active=True,
            ),
        )
        print(
            f"Admin user created: username={settings.INITIAL_ADMIN_USERNAME} "
            f"email={settings.INITIAL_ADMIN_EMAIL}"
        )
        print("⚠️  Change INITIAL_ADMIN_PASSWORD in .env and the user's password after first login.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
