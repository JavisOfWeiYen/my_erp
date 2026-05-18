from datetime import date

from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser, DbDep
from app.crud import accounts_payable as ap_crud
from app.models.accounts_payable import PayableStatus
from app.schemas.accounts_payable import AccountsPayableRead, APAgingReport

router = APIRouter(prefix="/accounts-payable", tags=["accounts-payable"])


@router.get("", response_model=list[AccountsPayableRead])
def list_payables(
    db: DbDep,
    _: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    supplier_id: int | None = None,
    status_filter: PayableStatus | None = None,
    issued_from: date | None = None,
    issued_to: date | None = None,
    overdue_only: bool = False,
    search: str | None = None,
) -> list[AccountsPayableRead]:
    return ap_crud.list_all(
        db,
        skip=skip,
        limit=limit,
        supplier_id=supplier_id,
        status_filter=status_filter,
        issued_from=issued_from,
        issued_to=issued_to,
        overdue_only=overdue_only,
        search=search,
    )


@router.get("/aging", response_model=APAgingReport)
def get_ap_aging(
    db: DbDep,
    _: CurrentUser,
    as_of: date | None = None,
) -> APAgingReport:
    return ap_crud.aging_report(db, as_of=as_of)


@router.get("/{ap_id}", response_model=AccountsPayableRead)
def get_payable(ap_id: int, db: DbDep, _: CurrentUser) -> AccountsPayableRead:
    ap = ap_crud.get(db, ap_id)
    if not ap:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Accounts payable not found")
    return ap
