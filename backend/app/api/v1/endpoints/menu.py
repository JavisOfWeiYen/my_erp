from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import CurrentUser, DbDep, require_roles
from app.crud import menu_item as menu_crud
from app.models.user import User
from app.schemas.menu_item import (
    MenuItemCreate,
    MenuItemRead,
    MenuItemUpdate,
    ReorderEntry,
)

router = APIRouter(tags=["menu"])
admin_router = APIRouter(prefix="/admin/menu", tags=["menu-admin"])

require_admin = require_roles("admin")


@router.get("/menu", response_model=list[MenuItemRead])
def get_current_user_menu(db: DbDep, current_user: CurrentUser) -> list[MenuItemRead]:
    """Tree visible to the current user (filtered by role + active=true)."""
    role_name = current_user.role.name if current_user.role else ""
    return menu_crud.tree_for_role(db, role_name)


@admin_router.get("", response_model=list[MenuItemRead])
def list_all_menu_items(
    db: DbDep, _: User = Depends(require_admin)
) -> list[MenuItemRead]:
    """Full tree including inactive items, for the admin UI."""
    return menu_crud.admin_tree(db)


@admin_router.post("", response_model=MenuItemRead, status_code=status.HTTP_201_CREATED)
def create_menu_item(
    payload: MenuItemCreate,
    db: DbDep,
    _: User = Depends(require_admin),
) -> MenuItemRead:
    return MenuItemRead.model_validate(menu_crud.create(db, payload))


@admin_router.patch("/{item_id}", response_model=MenuItemRead)
def update_menu_item(
    item_id: int,
    payload: MenuItemUpdate,
    db: DbDep,
    _: User = Depends(require_admin),
) -> MenuItemRead:
    item = menu_crud.get(db, item_id)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Menu item not found")
    updated = menu_crud.update(db, item, payload)
    return MenuItemRead.model_validate(updated)


@admin_router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_menu_item(
    item_id: int,
    db: DbDep,
    _: User = Depends(require_admin),
) -> None:
    item = menu_crud.get(db, item_id)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Menu item not found")
    menu_crud.delete(db, item)


@admin_router.post("/reorder", status_code=status.HTTP_204_NO_CONTENT)
def reorder_menu(
    entries: list[ReorderEntry],
    db: DbDep,
    _: User = Depends(require_admin),
) -> None:
    menu_crud.reorder(db, entries)
