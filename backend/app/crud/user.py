from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


def _base_query():
    return select(User).options(selectinload(User.role))


def get(db: Session, user_id: int) -> User | None:
    return db.scalar(_base_query().where(User.id == user_id))


def get_by_username(db: Session, username: str) -> User | None:
    return db.scalar(_base_query().where(User.username == username))


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(_base_query().where(User.email == email))


def list_all(db: Session, *, skip: int = 0, limit: int = 100) -> list[User]:
    stmt = _base_query().order_by(User.id).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def create(db: Session, data: UserCreate) -> User:
    user = User(
        email=data.email,
        username=data.username,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        is_active=data.is_active,
        role_id=data.role_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return get(db, user.id)


def update(db: Session, user: User, data: UserUpdate) -> User:
    payload = data.model_dump(exclude_unset=True)
    if "password" in payload and payload["password"]:
        user.hashed_password = hash_password(payload.pop("password"))
    else:
        payload.pop("password", None)
    for field, value in payload.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return get(db, user.id)


def delete(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()


def authenticate(db: Session, username: str, password: str) -> User | None:
    user = get_by_username(db, username)
    if not user:
        user = get_by_email(db, username)
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
