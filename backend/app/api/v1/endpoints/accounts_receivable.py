from datetime import date

from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser, DbDep
from app.crud import accounts_receivable as ar_crud
from app.models.accounts_receivable import ReceivableStatus
from app.schemas.accounts_receivable import AccountsReceivableRead, ARAgingReport

router = APIRouter(prefix="/accounts-receivable", tags=["accounts-receivable"])


@router.get("", response_model=list[AccountsReceivableRead])
def list_receivables(
    db: DbDep,
    _: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    customer_id: int | None = None,
    status_filter: ReceivableStatus | None = None,
    issued_from: date | None = None,
    issued_to: date | None = None,
    overdue_only: bool = False,
    search: str | None = None,
) -> list[AccountsReceivableRead]:
    return ar_crud.list_all(
        db,
        skip=skip,
        limit=limit,
        customer_id=customer_id,
        status_filter=status_filter,
        issued_from=issued_from,
        issued_to=issued_to,
        overdue_only=overdue_only,
        search=search,
    )


@router.get("/aging", response_model=ARAgingReport)
def get_ar_aging(
    db: DbDep,
    _: CurrentUser,
    as_of: date | None = None,
) -> ARAgingReport:
    return ar_crud.aging_report(db, as_of=as_of)


@router.get("/{ar_id}", response_model=AccountsReceivableRead)
def get_receivable(ar_id: int, db: DbDep, _: CurrentUser) -> AccountsReceivableRead:
    ar = ar_crud.get(db, ar_id)
    if not ar:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Accounts receivable not found")
    return ar
