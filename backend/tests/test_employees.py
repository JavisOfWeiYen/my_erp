from datetime import date
from decimal import Decimal

import pytest

from app.crud import role as role_crud
from app.crud import user as user_crud
from app.models.employee import Employee, SalaryRecord
from app.schemas.user import UserCreate


def _emp_payload(**overrides):
    base = {
        "department": "sales",
        "title": "業務專員",
        "hire_date": "2024-01-15",
        "employment_type": "full_time",
        "initial_salary": "50000.00",
    }
    base.update(overrides)
    return base


def _make_extra_user(db_session, roles, username):
    return user_crud.create(
        db_session,
        UserCreate(
            username=username,
            email=f"{username}@example.com",
            full_name=username.title(),
            password="testpass123",
            role_id=roles["sales"].id,
            is_active=True,
        ),
    )


def test_create_employee_generates_number_and_initial_salary_record(db_session, auth, users, roles):
    sales_user = _make_extra_user(db_session, roles, "alice_sales")
    admin = auth("admin")

    r = admin.post(
        "/api/v1/employees",
        json=_emp_payload(user_id=sales_user.id),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["employee_number"] == "E-2024-0001"
    assert body["department"] == "sales"
    assert Decimal(body["base_salary"]) == Decimal("50000.00")
    assert body["user"]["username"] == "alice_sales"

    db_session.expire_all()
    records = db_session.query(SalaryRecord).filter_by(employee_id=body["id"]).all()
    assert len(records) == 1
    assert records[0].reason.value == "hire"
    assert records[0].amount == Decimal("50000.00")
    assert records[0].effective_date == date(2024, 1, 15)


def test_create_employee_without_user_id_allowed(db_session, auth):
    admin = auth("admin")
    r = admin.post("/api/v1/employees", json=_emp_payload())
    assert r.status_code == 201
    assert r.json()["user"] is None


def test_create_employee_with_nonexistent_user_id_rejected(db_session, auth):
    admin = auth("admin")
    r = admin.post("/api/v1/employees", json=_emp_payload(user_id=99999))
    assert r.status_code == 400
    assert "user_id" in r.json()["detail"].lower()


def test_user_id_one_to_one_unique(db_session, auth, roles):
    extra = _make_extra_user(db_session, roles, "bob_sales")
    admin = auth("admin")

    r1 = admin.post("/api/v1/employees", json=_emp_payload(user_id=extra.id))
    assert r1.status_code == 201

    r2 = admin.post(
        "/api/v1/employees",
        json=_emp_payload(user_id=extra.id, hire_date="2024-02-01"),
    )
    assert r2.status_code == 409
    assert "already" in r2.json()["detail"].lower()


def test_employee_number_increments_within_same_year(db_session, auth):
    admin = auth("admin")
    nums = []
    for _ in range(3):
        r = admin.post("/api/v1/employees", json=_emp_payload())
        assert r.status_code == 201
        nums.append(r.json()["employee_number"])
    assert nums == ["E-2024-0001", "E-2024-0002", "E-2024-0003"]


def test_employee_number_year_follows_hire_date(db_session, auth):
    admin = auth("admin")
    r1 = admin.post("/api/v1/employees", json=_emp_payload(hire_date="2024-06-01"))
    r2 = admin.post("/api/v1/employees", json=_emp_payload(hire_date="2025-03-15"))
    assert r1.json()["employee_number"].startswith("E-2024-")
    assert r2.json()["employee_number"].startswith("E-2025-")


def test_list_filters_by_department_and_terminated(db_session, auth):
    admin = auth("admin")
    admin.post("/api/v1/employees", json=_emp_payload(department="sales"))
    admin.post("/api/v1/employees", json=_emp_payload(department="warehouse"))
    admin.post(
        "/api/v1/employees",
        json=_emp_payload(department="sales", termination_date="2025-01-01"),
    )

    # Default excludes terminated.
    r = admin.get("/api/v1/employees")
    assert len(r.json()) == 2

    # include_terminated=true brings the terminated row back.
    r = admin.get("/api/v1/employees?include_terminated=true")
    assert len(r.json()) == 3

    # Filter by department.
    r = admin.get("/api/v1/employees?department=warehouse")
    assert len(r.json()) == 1
    assert r.json()[0]["department"] == "warehouse"


def test_patch_employee_updates_fields(db_session, auth):
    admin = auth("admin")
    r = admin.post("/api/v1/employees", json=_emp_payload())
    emp_id = r.json()["id"]

    r2 = admin.patch(
        f"/api/v1/employees/{emp_id}",
        json={"title": "資深業務", "termination_date": "2026-05-01"},
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["title"] == "資深業務"
    assert body["termination_date"] == "2026-05-01"

    # base_salary is not changed by patch (only by adding salary records).
    assert Decimal(body["base_salary"]) == Decimal("50000.00")


def test_add_salary_record_updates_cached_base_salary(db_session, auth):
    admin = auth("admin")
    r = admin.post("/api/v1/employees", json=_emp_payload())
    emp_id = r.json()["id"]

    r2 = admin.post(
        f"/api/v1/employees/{emp_id}/salary-records",
        json={
            "effective_date": "2025-07-01",
            "amount": "60000.00",
            "reason": "promotion",
            "notes": "promoted to senior",
        },
    )
    assert r2.status_code == 201
    assert Decimal(r2.json()["amount"]) == Decimal("60000.00")

    db_session.expire_all()
    emp = db_session.get(Employee, emp_id)
    assert emp.base_salary == Decimal("60000.00")


def test_past_dated_salary_record_does_not_update_base_salary(db_session, auth):
    admin = auth("admin")
    r = admin.post("/api/v1/employees", json=_emp_payload(hire_date="2024-01-15"))
    emp_id = r.json()["id"]

    # Promote in 2025-07.
    admin.post(
        f"/api/v1/employees/{emp_id}/salary-records",
        json={"effective_date": "2025-07-01", "amount": "60000.00", "reason": "promotion"},
    )
    # Now add a backdated correction earlier than the promotion — should NOT
    # overwrite the cached current salary.
    r3 = admin.post(
        f"/api/v1/employees/{emp_id}/salary-records",
        json={"effective_date": "2024-12-01", "amount": "55000.00", "reason": "correction"},
    )
    assert r3.status_code == 201

    db_session.expire_all()
    emp = db_session.get(Employee, emp_id)
    assert emp.base_salary == Decimal("60000.00")


def test_salary_records_returned_newest_first(db_session, auth):
    admin = auth("admin")
    r = admin.post("/api/v1/employees", json=_emp_payload(hire_date="2024-01-15"))
    emp_id = r.json()["id"]
    admin.post(
        f"/api/v1/employees/{emp_id}/salary-records",
        json={"effective_date": "2025-07-01", "amount": "60000", "reason": "promotion"},
    )

    r2 = admin.get(f"/api/v1/employees/{emp_id}/salary-records")
    dates = [row["effective_date"] for row in r2.json()]
    assert dates == ["2025-07-01", "2024-01-15"]


def test_delete_employee_cascades_salary_records(db_session, auth):
    admin = auth("admin")
    r = admin.post("/api/v1/employees", json=_emp_payload())
    emp_id = r.json()["id"]
    admin.post(
        f"/api/v1/employees/{emp_id}/salary-records",
        json={"effective_date": "2025-07-01", "amount": "60000", "reason": "promotion"},
    )

    r2 = admin.delete(f"/api/v1/employees/{emp_id}")
    assert r2.status_code == 204

    db_session.expire_all()
    assert db_session.get(Employee, emp_id) is None
    remaining = db_session.query(SalaryRecord).filter_by(employee_id=emp_id).all()
    assert remaining == []


@pytest.mark.parametrize("role", ["manager", "sales", "warehouse"])
def test_non_admin_cannot_access(role, db_session, auth):
    c = auth(role)
    # All endpoints admin only.
    assert c.get("/api/v1/employees").status_code == 403
    assert c.post("/api/v1/employees", json=_emp_payload()).status_code == 403
    assert c.get("/api/v1/employees/1").status_code == 403
    assert c.patch("/api/v1/employees/1", json={"title": "x"}).status_code == 403
    assert c.delete("/api/v1/employees/1").status_code == 403
    assert c.get("/api/v1/employees/1/salary-records").status_code == 403
    assert c.post(
        "/api/v1/employees/1/salary-records",
        json={"effective_date": "2025-01-01", "amount": "1", "reason": "adjustment"},
    ).status_code == 403
