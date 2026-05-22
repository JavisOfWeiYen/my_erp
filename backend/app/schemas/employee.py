from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.employee import Department, EmploymentType, SalaryChangeReason


class EmployeeBase(BaseModel):
    user_id: int | None = None
    department: Department
    title: str = Field(min_length=1, max_length=64)
    hire_date: date
    termination_date: date | None = None
    employment_type: EmploymentType = EmploymentType.full_time
    notes: str | None = Field(default=None, max_length=500)


class EmployeeCreate(EmployeeBase):
    initial_salary: Decimal = Field(ge=0, max_digits=10, decimal_places=2)


class EmployeeUpdate(BaseModel):
    user_id: int | None = None
    department: Department | None = None
    title: str | None = Field(default=None, min_length=1, max_length=64)
    hire_date: date | None = None
    termination_date: date | None = None
    employment_type: EmploymentType | None = None
    notes: str | None = Field(default=None, max_length=500)


class EmployeeUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    full_name: str | None
    email: EmailStr | None


class EmployeeRead(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_number: str
    base_salary: Decimal
    user: EmployeeUserRead | None
    created_at: datetime
    updated_at: datetime


class SalaryRecordCreate(BaseModel):
    effective_date: date
    amount: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    reason: SalaryChangeReason
    notes: str | None = Field(default=None, max_length=500)


class SalaryRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_id: int
    effective_date: date
    amount: Decimal
    reason: SalaryChangeReason
    notes: str | None
    created_by_id: int
    created_at: datetime
