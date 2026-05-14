from fastapi import APIRouter

from app.core.deps import CurrentUser, DbDep
from app.crud import dashboard as dashboard_crud
from app.schemas.dashboard import DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_summary(db: DbDep, _: CurrentUser) -> DashboardSummary:
    return dashboard_crud.summary(db)
