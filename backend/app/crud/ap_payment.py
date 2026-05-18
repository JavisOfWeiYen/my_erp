from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.accounts_payable import AccountsPayable, PayableStatus
from app.models.ap_payment import APPayment
from app.schemas.ap_payment import APPaymentCreate


def _base_query():
    return select(APPayment).options(
        selectinload(APPayment.operator),
        selectinload(APPayment.voided_by),
    )


def get(db: Session, payment_id: int) -> APPayment | None:
    return db.scalar(_base_query().where(APPayment.id == payment_id))


def list_for_ap(db: Session, ap_id: int) -> list[APPayment]:
    stmt = (
        _base_query()
        .where(APPayment.accounts_payable_id == ap_id)
        .order_by(APPayment.paid_at, APPayment.id)
    )
    return list(db.scalars(stmt))


def generate_payment_number(db: Session, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    date_part = now.strftime("%Y%m%d")
    prefix = f"PAY-{date_part}-"
    count = db.scalar(
        select(func.count(APPayment.id)).where(APPayment.payment_number.like(f"{prefix}%"))
    )
    seq = (count or 0) + 1
    return f"{prefix}{seq:04d}"


def create(db: Session, data: APPaymentCreate, *, operator_id: int) -> APPayment:
    ap = db.scalar(
        select(AccountsPayable).where(AccountsPayable.id == data.accounts_payable_id)
    )
    if not ap:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Accounts payable does not exist")
    if ap.status in (PayableStatus.paid, PayableStatus.voided):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot record payment: payable is already {ap.status.value}",
        )

    amount = Decimal(data.amount)
    new_paid = ap.paid_amount + amount
    if new_paid > ap.amount_total:
        balance = ap.amount_total - ap.paid_amount
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Payment {amount} exceeds outstanding balance {balance}",
        )

    paid_at = data.paid_at or datetime.now(timezone.utc)
    payment = APPayment(
        payment_number=generate_payment_number(db, paid_at),
        accounts_payable_id=ap.id,
        amount=amount,
        method=data.method,
        paid_at=paid_at,
        reference=data.reference,
        notes=data.notes,
        operator_id=operator_id,
    )
    db.add(payment)

    ap.paid_amount = new_paid
    ap.status = (
        PayableStatus.paid
        if new_paid == ap.amount_total
        else PayableStatus.partial
    )
    db.commit()
    return get(db, payment.id)


def void(
    db: Session,
    payment: APPayment,
    *,
    operator_id: int,
    reason: str | None,
) -> APPayment:
    if payment.voided_at is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Payment is already voided"
        )
    ap = db.scalar(
        select(AccountsPayable).where(
            AccountsPayable.id == payment.accounts_payable_id
        )
    )
    if ap is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Linked payable not found"
        )

    new_paid = ap.paid_amount - payment.amount
    if new_paid < Decimal("0"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Void would drive paid_amount below zero — refuse",
        )

    ap.paid_amount = new_paid
    if new_paid == Decimal("0"):
        ap.status = PayableStatus.open
    elif new_paid < ap.amount_total:
        ap.status = PayableStatus.partial
    else:
        ap.status = PayableStatus.paid

    payment.voided_at = datetime.now(timezone.utc)
    payment.voided_by_id = operator_id
    payment.void_reason = reason
    db.commit()
    return get(db, payment.id)
