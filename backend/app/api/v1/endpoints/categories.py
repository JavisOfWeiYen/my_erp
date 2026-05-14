from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import CurrentUser, DbDep, require_roles
from app.crud import category as category_crud
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])

require_writer = require_roles("admin", "manager")


@router.get("", response_model=list[CategoryRead])
def list_categories(
    db: DbDep,
    _: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> list[CategoryRead]:
    return category_crud.list_all(db, skip=skip, limit=limit)


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: DbDep,
    _: User = Depends(require_writer),
) -> CategoryRead:
    if category_crud.get_by_name(db, payload.name):
        raise HTTPException(status.HTTP_409_CONFLICT, "Category name already exists")
    return category_crud.create(db, payload)


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(
    category_id: int,
    db: DbDep,
    _: CurrentUser,
) -> CategoryRead:
    category = category_crud.get(db, category_id)
    if not category:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    return category


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: DbDep,
    _: User = Depends(require_writer),
) -> CategoryRead:
    category = category_crud.get(db, category_id)
    if not category:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    if payload.name and payload.name != category.name:
        existing = category_crud.get_by_name(db, payload.name)
        if existing and existing.id != category.id:
            raise HTTPException(status.HTTP_409_CONFLICT, "Category name already exists")
    return category_crud.update(db, category, payload)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: DbDep,
    _: User = Depends(require_writer),
) -> None:
    category = category_crud.get(db, category_id)
    if not category:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    category_crud.delete(db, category)
