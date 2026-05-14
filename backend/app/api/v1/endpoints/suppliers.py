from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import CurrentUser, DbDep, require_roles
from app.crud import supplier as supplier_crud
from app.models.user import User
from app.schemas.supplier import SupplierCreate, SupplierRead, SupplierUpdate

router = APIRouter(prefix="/suppliers", tags=["suppliers"])

require_writer = require_roles("admin", "manager")


@router.get("", response_model=list[SupplierRead])
def list_suppliers(
    db: DbDep,
    _: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    is_active: bool | None = None,
) -> list[SupplierRead]:
    return supplier_crud.list_all(
        db, skip=skip, limit=limit, search=search, is_active=is_active
    )


@router.post("", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
def create_supplier(
    payload: SupplierCreate,
    db: DbDep,
    _: User = Depends(require_writer),
) -> SupplierRead:
    if supplier_crud.get_by_name(db, payload.name):
        raise HTTPException(status.HTTP_409_CONFLICT, "Supplier name already exists")
    return supplier_crud.create(db, payload)


@router.get("/{supplier_id}", response_model=SupplierRead)
def get_supplier(
    supplier_id: int,
    db: DbDep,
    _: CurrentUser,
) -> SupplierRead:
    supplier = supplier_crud.get(db, supplier_id)
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplier not found")
    return supplier


@router.patch("/{supplier_id}", response_model=SupplierRead)
def update_supplier(
    supplier_id: int,
    payload: SupplierUpdate,
    db: DbDep,
    _: User = Depends(require_writer),
) -> SupplierRead:
    supplier = supplier_crud.get(db, supplier_id)
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplier not found")
    if payload.name and payload.name != supplier.name:
        existing = supplier_crud.get_by_name(db, payload.name)
        if existing and existing.id != supplier.id:
            raise HTTPException(status.HTTP_409_CONFLICT, "Supplier name already exists")
    return supplier_crud.update(db, supplier, payload)


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(
    supplier_id: int,
    db: DbDep,
    _: User = Depends(require_writer),
) -> None:
    supplier = supplier_crud.get(db, supplier_id)
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplier not found")
    if supplier.purchases:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Supplier has purchase records and cannot be deleted; deactivate it instead",
        )
    supplier_crud.delete(db, supplier)
