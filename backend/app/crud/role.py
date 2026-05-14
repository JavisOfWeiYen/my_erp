from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.role import Role


def get(db: Session, role_id: int) -> Role | None:
    return db.get(Role, role_id)


def get_by_name(db: Session, name: str) -> Role | None:
    return db.scalar(select(Role).where(Role.name == name))


def list_all(db: Session) -> list[Role]:
    return list(db.scalars(select(Role).order_by(Role.id)))


def create(db: Session, *, name: str, description: str | None = None) -> Role:
    role = Role(name=name, description=description)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role
