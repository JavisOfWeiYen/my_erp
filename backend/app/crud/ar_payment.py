from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.accounts_receivable import AccountsReceivable, ReceivableStatus
from app.models.ar_payment import ARPayment
from app.schemas.ar_payment import ARPaymentCreate


def _base_query():
    return select(ARPayment).options(
        selectinload(ARPayment.operator),
        selectinload(ARPayment.voided_by),
    )


def get(db: Session, payment_id: int) -> ARPayment | None:
    return db.scalar(_base_query().where(ARPayment.id == payment_id))


def list_for_ar(db: Session, ar_id: int) -> list[ARPayment]:
    stmt = (
        _base_query()
        .where(ARPayment.accounts_receivable_id == ar_id)
        .order_by(ARPayment.paid_at, ARPayment.id)
    )
    return list(db.scalars(stmt))


def generate_payment_number(db: Session, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    date_part = now.strftime("%Y%m%d")
    prefix = f"REC-{date_part}-"
    count = db.scalar(
        select(func.count(ARPayment.id)).where(ARPayment.payment_number.like(f"{prefix}%"))
    )
    seq = (count or 0) + 1
    return f"{prefix}{seq:04d}"


def create(db: Session, data: ARPaymentCreate, *, operator_id: int) -> ARPayment:
    ar = db.scalar(
        select(AccountsReceivable).where(AccountsReceivable.id == data.accounts_receivable_id)
    )
    if not ar:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Accounts receivable does not exist")
    if ar.status in (ReceivableStatus.paid, ReceivableStatus.voided):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot record payment: receivable is already {ar.status.value}",
        )

    amount = Decimal(data.amount)
    new_paid = ar.paid_amount + amount
    if new_paid > ar.amount_total:
        balance = ar.amount_total - ar.paid_amount
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Payment {amount} exceeds outstanding balance {balance}",
        )

    paid_at = data.paid_at or datetime.now(timezone.utc)
    payment = ARPayment(
        payment_number=generate_payment_number(db, paid_at),
        accounts_receivable_id=ar.id,
        amount=amount,
        method=data.method,
        paid_at=paid_at,
        reference=data.reference,
        notes=data.notes,
        operator_id=operator_id,
    )
    db.add(payment)

    ar.paid_amount = new_paid
    ar.status = (
        ReceivableStatus.paid
        if new_paid == ar.amount_total
        else ReceivableStatus.partial
    )
    db.commit()
    return get(db, payment.id)


def void(
    db: Session,
    payment: ARPayment,
    *,
    operator_id: int,
    reason: str | None,
) -> ARPayment:
    """Reverse a previously-recorded receipt.

    Marks the payment row as voided (audit trail preserved) and decrements the
    parent AR's paid_amount + recomputes its status. Idempotent guard: a payment
    already voided cannot be voided again."""
    if payment.voided_at is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Payment is already voided"
        )
    ar = db.scalar(
        select(AccountsReceivable).where(
            AccountsReceivable.id == payment.accounts_receivable_id
        )
    )
    if ar is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Linked receivable not found"
        )

    new_paid = ar.paid_amount - payment.amount
    if new_paid < Decimal("0"):
        # Should not happen unless data has drifted; be defensive.
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Void would drive paid_amount below zero — refuse",
        )

    ar.paid_amount = new_paid
    if new_paid == Decimal("0"):
        ar.status = ReceivableStatus.open
    elif new_paid < ar.amount_total:
        ar.status = ReceivableStatus.partial
    else:
        ar.status = ReceivableStatus.paid

    payment.voided_at = datetime.now(timezone.utc)
    payment.voided_by_id = operator_id
    payment.void_reason = reason
    db.commit()
    return get(db, payment.id)
