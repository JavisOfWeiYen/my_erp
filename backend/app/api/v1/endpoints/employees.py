from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import DbDep, require_roles
from app.crud import employee as employee_crud
from app.models.employee import Department
from app.models.user import User
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeRead,
    EmployeeUpdate,
    SalaryRecordCreate,
    SalaryRecordRead,
)

router = APIRouter(prefix="/employees", tags=["employees"])

require_admin = require_roles("admin")


@router.get("", response_model=list[EmployeeRead])
def list_employees(
    db: DbDep,
    _: User = Depends(require_admin),
    skip: int = 0,
    limit: int = 100,
    department: Department | None = None,
    include_terminated: bool = False,
    search: str | None = None,
) -> list[EmployeeRead]:
    return employee_crud.list_all(
        db,
        skip=skip,
        limit=limit,
        department=department,
        include_terminated=include_terminated,
        search=search,
    )


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: DbDep,
    current_user: User = Depends(require_admin),
) -> EmployeeRead:
    return employee_crud.create(db, payload, created_by_id=current_user.id)


@router.get("/{employee_id}", response_model=EmployeeRead)
def get_employee(
    employee_id: int,
    db: DbDep,
    _: User = Depends(require_admin),
) -> EmployeeRead:
    emp = employee_crud.get(db, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    return emp


@router.patch("/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: DbDep,
    _: User = Depends(require_admin),
) -> EmployeeRead:
    emp = employee_crud.get(db, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    return employee_crud.update(db, emp, payload)


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: int,
    db: DbDep,
    _: User = Depends(require_admin),
) -> None:
    emp = employee_crud.get(db, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    employee_crud.delete(db, emp)


@router.get("/{employee_id}/salary-records", response_model=list[SalaryRecordRead])
def list_employee_salary_records(
    employee_id: int,
    db: DbDep,
    _: User = Depends(require_admin),
) -> list[SalaryRecordRead]:
    emp = employee_crud.get(db, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    return employee_crud.list_salary_records(db, employee_id)


@router.post(
    "/{employee_id}/salary-records",
    response_model=SalaryRecordRead,
    status_code=status.HTTP_201_CREATED,
)
def add_employee_salary_record(
    employee_id: int,
    payload: SalaryRecordCreate,
    db: DbDep,
    current_user: User = Depends(require_admin),
) -> SalaryRecordRead:
    emp = employee_crud.get(db, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    return employee_crud.add_salary_record(
        db, emp, payload, created_by_id=current_user.id
    )
