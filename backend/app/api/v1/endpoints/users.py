from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbDep, require_roles
from app.crud import role as role_crud
from app.crud import user as user_crud
from app.models.role import Role
from app.models.user import User
from app.schemas.user import UserBrief, UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

require_admin = require_roles("admin")


@router.get("", response_model=list[UserRead])
def list_users(
    db: DbDep,
    _: User = Depends(require_admin),
    skip: int = 0,
    limit: int = 100,
) -> list[UserRead]:
    return user_crud.list_all(db, skip=skip, limit=limit)


@router.get("/staff", response_model=list[UserBrief])
def list_staff(
    db: DbDep,
    _: CurrentUser,
    role_name: str | None = None,
    active_only: bool = True,
) -> list[UserBrief]:
    """Lightweight roster for selectors (e.g. salesperson picker).
    Accessible to any authenticated user — exposes only id/username/full_name/role_name.
    """
    stmt = select(User).options(selectinload(User.role))
    if active_only:
        stmt = stmt.where(User.is_active.is_(True))
    if role_name:
        stmt = stmt.join(Role).where(Role.name == role_name)
    stmt = stmt.order_by(User.username)
    rows = db.scalars(stmt).all()
    return [
        UserBrief(
            id=u.id,
            username=u.username,
            full_name=u.full_name,
            role_name=u.role.name if u.role else None,
        )
        for u in rows
    ]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: DbDep,
    _: User = Depends(require_admin),
) -> UserRead:
    if user_crud.get_by_username(db, payload.username):
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already exists")
    if user_crud.get_by_email(db, payload.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    if not role_crud.get(db, payload.role_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Role does not exist")
    return user_crud.create(db, payload)


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: int,
    db: DbDep,
    _: User = Depends(require_admin),
) -> UserRead:
    user = user_crud.get(db, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: DbDep,
    _: User = Depends(require_admin),
) -> UserRead:
    user = user_crud.get(db, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if payload.email and payload.email != user.email:
        existing = user_crud.get_by_email(db, payload.email)
        if existing and existing.id != user.id:
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    if payload.role_id and not role_crud.get(db, payload.role_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Role does not exist")
    return user_crud.update(db, user, payload)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: DbDep,
    current_user: User = Depends(require_admin),
) -> None:
    user = user_crud.get(db, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete yourself")
    user_crud.delete(db, user)
