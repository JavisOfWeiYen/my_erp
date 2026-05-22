from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.employee import (
    Department,
    Employee,
    SalaryChangeReason,
    SalaryRecord,
)
from app.models.user import User
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeUpdate,
    SalaryRecordCreate,
)


def _base_query():
    return select(Employee).options(selectinload(Employee.user))


def get(db: Session, employee_id: int) -> Employee | None:
    return db.scalar(_base_query().where(Employee.id == employee_id))


def get_by_user_id(db: Session, user_id: int) -> Employee | None:
    return db.scalar(_base_query().where(Employee.user_id == user_id))


def list_all(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    department: Department | None = None,
    include_terminated: bool = False,
    search: str | None = None,
) -> list[Employee]:
    stmt = _base_query()
    if department is not None:
        stmt = stmt.where(Employee.department == department)
    if not include_terminated:
        stmt = stmt.where(Employee.termination_date.is_(None))
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(
                Employee.employee_number.ilike(like),
                Employee.title.ilike(like),
            )
        )
    stmt = stmt.order_by(Employee.id).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def generate_employee_number(db: Session, *, year: int | None = None) -> str:
    year = year or datetime.now(timezone.utc).year
    prefix = f"E-{year}-"
    count = db.scalar(
        select(func.count(Employee.id)).where(
            Employee.employee_number.like(f"{prefix}%")
        )
    )
    seq = (count or 0) + 1
    return f"{prefix}{seq:04d}"


def _validate_user_id(db: Session, user_id: int | None, *, exclude_id: int | None = None) -> None:
    if user_id is None:
        return
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "user_id does not exist")
    existing = get_by_user_id(db, user_id)
    if existing and existing.id != exclude_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "User is already linked to another employee record",
        )


def create(db: Session, data: EmployeeCreate, *, created_by_id: int) -> Employee:
    _validate_user_id(db, data.user_id)

    emp = Employee(
        user_id=data.user_id,
        employee_number=generate_employee_number(db, year=data.hire_date.year),
        department=data.department,
        title=data.title,
        hire_date=data.hire_date,
        termination_date=data.termination_date,
        employment_type=data.employment_type,
        base_salary=data.initial_salary,
        notes=data.notes,
    )
    db.add(emp)
    db.flush()

    initial_record = SalaryRecord(
        employee_id=emp.id,
        effective_date=data.hire_date,
        amount=data.initial_salary,
        reason=SalaryChangeReason.hire,
        notes="Initial salary on hire",
        created_by_id=created_by_id,
    )
    db.add(initial_record)
    db.commit()
    return get(db, emp.id)


def update(db: Session, emp: Employee, data: EmployeeUpdate) -> Employee:
    update_data = data.model_dump(exclude_unset=True)
    if "user_id" in update_data and update_data["user_id"] != emp.user_id:
        _validate_user_id(db, update_data["user_id"], exclude_id=emp.id)
    for field, value in update_data.items():
        setattr(emp, field, value)
    db.commit()
    return get(db, emp.id)


def delete(db: Session, emp: Employee) -> None:
    db.delete(emp)
    db.commit()


def list_salary_records(db: Session, employee_id: int) -> list[SalaryRecord]:
    stmt = (
        select(SalaryRecord)
        .where(SalaryRecord.employee_id == employee_id)
        .order_by(SalaryRecord.effective_date.desc(), SalaryRecord.id.desc())
    )
    return list(db.scalars(stmt))


def add_salary_record(
    db: Session,
    emp: Employee,
    data: SalaryRecordCreate,
    *,
    created_by_id: int,
) -> SalaryRecord:
    record = SalaryRecord(
        employee_id=emp.id,
        effective_date=data.effective_date,
        amount=data.amount,
        reason=data.reason,
        notes=data.notes,
        created_by_id=created_by_id,
    )
    db.add(record)
    db.flush()

    # Refresh the cached base_salary only if this is now the latest effective row.
    latest = db.scalar(
        select(SalaryRecord)
        .where(SalaryRecord.employee_id == emp.id)
        .order_by(SalaryRecord.effective_date.desc(), SalaryRecord.id.desc())
        .limit(1)
    )
    if latest is not None and latest.id == record.id:
        emp.base_salary = data.amount

    db.commit()
    db.refresh(record)
    return record
