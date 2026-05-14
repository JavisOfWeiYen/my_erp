from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import CurrentUser, DbDep, require_roles
from app.crud import customer as customer_crud
from app.crud import sales_order as so_crud
from app.models.sales_order import SalesOrderStatus
from app.models.user import User
from app.schemas.sales_order import (
    SalesOrderCreate,
    SalesOrderRead,
    SalesOrderUpdate,
)

router = APIRouter(prefix="/sales-orders", tags=["sales-orders"])

require_writer = require_roles("admin", "manager", "sales")


@router.get("", response_model=list[SalesOrderRead])
def list_sales_orders(
    db: DbDep,
    _: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    customer_id: int | None = None,
    salesperson_id: int | None = None,
    status_filter: SalesOrderStatus | None = None,
    search: str | None = None,
) -> list[SalesOrderRead]:
    return so_crud.list_all(
        db,
        skip=skip,
        limit=limit,
        customer_id=customer_id,
        salesperson_id=salesperson_id,
        status_filter=status_filter,
        search=search,
    )


@router.post("", response_model=SalesOrderRead, status_code=status.HTTP_201_CREATED)
def create_sales_order(
    payload: SalesOrderCreate,
    db: DbDep,
    current_user: User = Depends(require_writer),
) -> SalesOrderRead:
    customer = customer_crud.get(db, payload.customer_id)
    if not customer:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Customer does not exist")
    if not customer.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Customer is inactive")
    return so_crud.create_draft(
        db, payload, customer=customer, created_by_id=current_user.id
    )


@router.get("/{sales_order_id}", response_model=SalesOrderRead)
def get_sales_order(
    sales_order_id: int,
    db: DbDep,
    _: CurrentUser,
) -> SalesOrderRead:
    order = so_crud.get(db, sales_order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sales order not found")
    return order


@router.patch("/{sales_order_id}", response_model=SalesOrderRead)
def update_sales_order(
    sales_order_id: int,
    payload: SalesOrderUpdate,
    db: DbDep,
    _: User = Depends(require_writer),
) -> SalesOrderRead:
    order = so_crud.get(db, sales_order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sales order not found")
    customer = None
    if payload.customer_id is not None and payload.customer_id != order.customer_id:
        customer = customer_crud.get(db, payload.customer_id)
        if not customer:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Customer does not exist")
        if not customer.is_active:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Customer is inactive")
    return so_crud.update_draft(db, order, payload, customer=customer)


@router.post("/{sales_order_id}/cancel", response_model=SalesOrderRead)
def cancel_sales_order(
    sales_order_id: int,
    db: DbDep,
    _: User = Depends(require_writer),
) -> SalesOrderRead:
    order = so_crud.get(db, sales_order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sales order not found")
    return so_crud.cancel(db, order)


@router.post("/{sales_order_id}/confirm", response_model=SalesOrderRead)
def confirm_sales_order(
    sales_order_id: int,
    db: DbDep,
    _: User = Depends(require_writer),
) -> SalesOrderRead:
    order = so_crud.get(db, sales_order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sales order not found")
    return so_crud.confirm(db, order)
