from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import CurrentUser, DbDep, require_roles
from app.crud import customer as customer_crud
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["customers"])

require_writer = require_roles("admin", "manager", "sales")


@router.get("", response_model=list[CustomerRead])
def list_customers(
    db: DbDep,
    _: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    is_active: bool | None = None,
) -> list[CustomerRead]:
    return customer_crud.list_all(
        db, skip=skip, limit=limit, search=search, is_active=is_active
    )


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate,
    db: DbDep,
    _: User = Depends(require_writer),
) -> CustomerRead:
    if customer_crud.get_by_name(db, payload.name):
        raise HTTPException(status.HTTP_409_CONFLICT, "Customer name already exists")
    return customer_crud.create(db, payload)


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(
    customer_id: int,
    db: DbDep,
    _: CurrentUser,
) -> CustomerRead:
    customer = customer_crud.get(db, customer_id)
    if not customer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return customer


@router.patch("/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    db: DbDep,
    _: User = Depends(require_writer),
) -> CustomerRead:
    customer = customer_crud.get(db, customer_id)
    if not customer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    if payload.name and payload.name != customer.name:
        existing = customer_crud.get_by_name(db, payload.name)
        if existing and existing.id != customer.id:
            raise HTTPException(status.HTTP_409_CONFLICT, "Customer name already exists")
    return customer_crud.update(db, customer, payload)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: int,
    db: DbDep,
    _: User = Depends(require_writer),
) -> None:
    customer = customer_crud.get(db, customer_id)
    if not customer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    if customer.sales:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Customer has sales records and cannot be deleted; deactivate it instead",
        )
    customer_crud.delete(db, customer)
