from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import CurrentUser, DbDep, require_roles
from app.crud import purchase_order as po_crud
from app.crud import supplier as supplier_crud
from app.models.purchase_order import PurchaseOrderStatus
from app.models.user import User
from app.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderRead,
    PurchaseOrderUpdate,
)

router = APIRouter(prefix="/purchase-orders", tags=["purchase-orders"])

require_writer = require_roles("admin", "manager")
require_receiver = require_roles("admin", "manager", "warehouse")


@router.get("", response_model=list[PurchaseOrderRead])
def list_purchase_orders(
    db: DbDep,
    _: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    supplier_id: int | None = None,
    status_filter: PurchaseOrderStatus | None = None,
    search: str | None = None,
) -> list[PurchaseOrderRead]:
    return po_crud.list_all(
        db,
        skip=skip,
        limit=limit,
        supplier_id=supplier_id,
        status_filter=status_filter,
        search=search,
    )


@router.post("", response_model=PurchaseOrderRead, status_code=status.HTTP_201_CREATED)
def create_purchase_order(
    payload: PurchaseOrderCreate,
    db: DbDep,
    current_user: User = Depends(require_writer),
) -> PurchaseOrderRead:
    supplier = supplier_crud.get(db, payload.supplier_id)
    if not supplier:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Supplier does not exist")
    if not supplier.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Supplier is inactive")
    return po_crud.create_draft(
        db, payload, supplier=supplier, created_by_id=current_user.id
    )


@router.get("/{purchase_order_id}", response_model=PurchaseOrderRead)
def get_purchase_order(
    purchase_order_id: int,
    db: DbDep,
    _: CurrentUser,
) -> PurchaseOrderRead:
    order = po_crud.get(db, purchase_order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Purchase order not found")
    return order


@router.patch("/{purchase_order_id}", response_model=PurchaseOrderRead)
def update_purchase_order(
    purchase_order_id: int,
    payload: PurchaseOrderUpdate,
    db: DbDep,
    _: User = Depends(require_writer),
) -> PurchaseOrderRead:
    order = po_crud.get(db, purchase_order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Purchase order not found")
    supplier = None
    if payload.supplier_id is not None and payload.supplier_id != order.supplier_id:
        supplier = supplier_crud.get(db, payload.supplier_id)
        if not supplier:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Supplier does not exist")
        if not supplier.is_active:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Supplier is inactive")
    return po_crud.update_draft(db, order, payload, supplier=supplier)


@router.post("/{purchase_order_id}/cancel", response_model=PurchaseOrderRead)
def cancel_purchase_order(
    purchase_order_id: int,
    db: DbDep,
    _: User = Depends(require_writer),
) -> PurchaseOrderRead:
    order = po_crud.get(db, purchase_order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Purchase order not found")
    return po_crud.cancel(db, order)


@router.post("/{purchase_order_id}/receive", response_model=PurchaseOrderRead)
def receive_purchase_order(
    purchase_order_id: int,
    db: DbDep,
    _: User = Depends(require_receiver),
) -> PurchaseOrderRead:
    order = po_crud.get(db, purchase_order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Purchase order not found")
    return po_crud.receive(db, order)
