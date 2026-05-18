from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import CurrentUser, DbDep, require_roles
from app.crud import ap_payment as payment_crud
from app.models.user import User
from app.schemas.ap_payment import APPaymentCreate, APPaymentRead, APPaymentVoid

router = APIRouter(prefix="/ap-payments", tags=["ap-payments"])

require_writer = require_roles("admin", "manager")


@router.get("", response_model=list[APPaymentRead])
def list_ap_payments(
    db: DbDep,
    _: CurrentUser,
    accounts_payable_id: int,
) -> list[APPaymentRead]:
    return payment_crud.list_for_ap(db, accounts_payable_id)


@router.post("", response_model=APPaymentRead, status_code=status.HTTP_201_CREATED)
def create_ap_payment(
    payload: APPaymentCreate,
    db: DbDep,
    current_user: User = Depends(require_writer),
) -> APPaymentRead:
    return payment_crud.create(db, payload, operator_id=current_user.id)


@router.get("/{payment_id}", response_model=APPaymentRead)
def get_ap_payment(payment_id: int, db: DbDep, _: CurrentUser) -> APPaymentRead:
    payment = payment_crud.get(db, payment_id)
    if not payment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "AP payment not found")
    return payment


@router.post("/{payment_id}/void", response_model=APPaymentRead)
def void_ap_payment(
    payment_id: int,
    payload: APPaymentVoid,
    db: DbDep,
    current_user: User = Depends(require_writer),
) -> APPaymentRead:
    payment = payment_crud.get(db, payment_id)
    if not payment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "AP payment not found")
    return payment_crud.void(
        db, payment, operator_id=current_user.id, reason=payload.reason
    )
