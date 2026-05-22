from datetime import date, datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Department(str, PyEnum):
    sales = "sales"
    warehouse = "warehouse"
    accounting = "accounting"
    management = "management"
    it = "it"


class EmploymentType(str, PyEnum):
    full_time = "full_time"
    part_time = "part_time"
    contractor = "contractor"


class SalaryChangeReason(str, PyEnum):
    hire = "hire"
    promotion = "promotion"
    adjustment = "adjustment"
    correction = "correction"


class Employee(Base):
    """HR record for a company employee.

    Separated from `users` because salary and HR metadata is sensitive and
    must not leak through endpoints that expose login accounts. A `user_id`
    of NULL means the employee has no login (e.g. contractor, terminated).
    `base_salary` is a cached mirror of the most recent SalaryRecord.amount —
    the source of truth is the SalaryRecord history.
    """

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        unique=True,
        nullable=True,
        index=True,
    )
    employee_number: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    department: Mapped[Department] = mapped_column(
        Enum(Department, name="employee_department"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(64), nullable=False)
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    termination_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    employment_type: Mapped[EmploymentType] = mapped_column(
        Enum(EmploymentType, name="employee_employment_type"),
        nullable=False,
        default=EmploymentType.full_time,
    )
    base_salary: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0")
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User | None"] = relationship()  # noqa: F821
    salary_records: Mapped[list["SalaryRecord"]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
        order_by="SalaryRecord.effective_date.desc()",
    )


class SalaryRecord(Base):
    """Append-only history of an employee's monthly base salary changes.

    One row per salary structure change (hire, raise, promotion, correction).
    Not a payroll record — does not represent monthly payment events.
    """

    __tablename__ = "salary_records"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_salary_records_amount_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    reason: Mapped[SalaryChangeReason] = mapped_column(
        Enum(SalaryChangeReason, name="salary_change_reason"),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    employee: Mapped["Employee"] = relationship(back_populates="salary_records")
    created_by: Mapped["User"] = relationship()  # noqa: F821
