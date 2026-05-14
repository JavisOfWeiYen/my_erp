from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import CurrentUser, DbDep, require_roles
from app.crud import stock_adjustment as adj_crud
from app.models.stock_adjustment import StockAdjustmentReason
from app.models.user import User
from app.schemas.stock_adjustment import (
    StockAdjustmentCreate,
    StockAdjustmentRead,
)

router = APIRouter(prefix="/stock-adjustments", tags=["stock-adjustments"])

require_writer = require_roles("admin", "manager", "warehouse")


@router.get("", response_model=list[StockAdjustmentRead])
def list_adjustments(
    db: DbDep,
    _: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    product_id: int | None = None,
    reason: StockAdjustmentReason | None = None,
    operator_id: int | None = None,
    search: str | None = None,
) -> list[StockAdjustmentRead]:
    return adj_crud.list_all(
        db,
        skip=skip,
        limit=limit,
        product_id=product_id,
        reason=reason,
        operator_id=operator_id,
        search=search,
    )


@router.post("", response_model=StockAdjustmentRead, status_code=status.HTTP_201_CREATED)
def create_adjustment(
    payload: StockAdjustmentCreate,
    db: DbDep,
    current_user: User = Depends(require_writer),
) -> StockAdjustmentRead:
    return adj_crud.create(db, payload, operator_id=current_user.id)


@router.get("/{adjustment_id}", response_model=StockAdjustmentRead)
def get_adjustment(
    adjustment_id: int,
    db: DbDep,
    _: CurrentUser,
) -> StockAdjustmentRead:
    adj = adj_crud.get(db, adjustment_id)
    if not adj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Stock adjustment not found")
    return adj
