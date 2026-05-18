from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import CurrentUser, DbDep, require_roles
from app.crud import ar_payment as payment_crud
from app.models.user import User
from app.schemas.ar_payment import ARPaymentCreate, ARPaymentRead, ARPaymentVoid

router = APIRouter(prefix="/ar-payments", tags=["ar-payments"])

require_writer = require_roles("admin", "manager", "sales")


@router.get("", response_model=list[ARPaymentRead])
def list_ar_payments(
    db: DbDep,
    _: CurrentUser,
    accounts_receivable_id: int,
) -> list[ARPaymentRead]:
    return payment_crud.list_for_ar(db, accounts_receivable_id)


@router.post("", response_model=ARPaymentRead, status_code=status.HTTP_201_CREATED)
def create_ar_payment(
    payload: ARPaymentCreate,
    db: DbDep,
    current_user: User = Depends(require_writer),
) -> ARPaymentRead:
    return payment_crud.create(db, payload, operator_id=current_user.id)


@router.get("/{payment_id}", response_model=ARPaymentRead)
def get_ar_payment(payment_id: int, db: DbDep, _: CurrentUser) -> ARPaymentRead:
    payment = payment_crud.get(db, payment_id)
    if not payment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "AR payment not found")
    return payment


@router.post("/{payment_id}/void", response_model=ARPaymentRead)
def void_ar_payment(
    payment_id: int,
    payload: ARPaymentVoid,
    db: DbDep,
    current_user: User = Depends(require_writer),
) -> ARPaymentRead:
    payment = payment_crud.get(db, payment_id)
    if not payment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "AR payment not found")
    return payment_crud.void(
        db, payment, operator_id=current_user.id, reason=payload.reason
    )
