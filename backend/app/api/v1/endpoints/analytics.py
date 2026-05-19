from datetime import date

from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import CurrentUser, DbDep
from app.crud import analytics as analytics_crud
from app.schemas.analytics import (
    MarginByCustomerReport,
    MarginByProductReport,
    MarginTrendReport,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/margin/by-product", response_model=MarginByProductReport)
def margin_by_product(
    db: DbDep,
    _: CurrentUser,
    start_date: date | None = None,
    end_date: date | None = None,
    sort_by: str = Query(
        "margin_rate",
        pattern="^(margin_rate|revenue|gross_profit|quantity)$",
    ),
    top: int = Query(50, ge=1, le=500),
) -> MarginByProductReport:
    try:
        return analytics_crud.margin_by_product(
            db,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            top=top,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.get("/margin/by-customer", response_model=MarginByCustomerReport)
def margin_by_customer(
    db: DbDep,
    _: CurrentUser,
    start_date: date | None = None,
    end_date: date | None = None,
    sort_by: str = Query(
        "margin_rate",
        pattern="^(margin_rate|revenue|gross_profit)$",
    ),
    top: int = Query(50, ge=1, le=500),
) -> MarginByCustomerReport:
    try:
        return analytics_crud.margin_by_customer(
            db,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            top=top,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.get("/margin/trend", response_model=MarginTrendReport)
def margin_trend(
    db: DbDep,
    _: CurrentUser,
    months: int = Query(12, ge=1, le=60),
) -> MarginTrendReport:
    try:
        return analytics_crud.margin_trend(db, months=months)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
