"""Create the demo HR tables in Neon and load four FAKE employees.

Run from the project root:
    python -m app.hr.seed_employees

Safe to re-run: employees are updated in place. All people and passwords below
are fictional demo data. Never reuse these passwords anywhere real.
"""

from datetime import date

from app.hr.auth import hash_password
from app.hr.repository import _connect

SCHEMA = """
CREATE TABLE IF NOT EXISTS hr_employees (
    employee_id   TEXT PRIMARY KEY,
    full_name     TEXT NOT NULL,
    designation   TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('employee', 'manager', 'hr_admin')),
    status        TEXT NOT NULL CHECK (status IN ('probation', 'confirmed')),
    joined_on     DATE NOT NULL,
    password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS hr_leave_usage (
    employee_id TEXT NOT NULL REFERENCES hr_employees(employee_id),
    year        INT  NOT NULL,
    cl_used     NUMERIC(4, 1) NOT NULL DEFAULT 0,
    sl_used     NUMERIC(4, 1) NOT NULL DEFAULT 0,
    el_used     NUMERIC(4, 1) NOT NULL DEFAULT 0,
    PRIMARY KEY (employee_id, year)
);
"""

# (id, name, designation, role, status, joined_on, demo password, CL used, SL used, EL used)
DEMO_USERS = [
    ("E1001", "Rahul Sharma", "Sales Executive", "employee", "confirmed", date(2024, 1, 15), "rahul@demo1", 5, 2, 6),
    ("E1002", "Priya Nair", "Sales Executive", "employee", "probation", date(2026, 7, 1), "priya@demo2", 2, 1, 0),
    ("E1003", "Amit Verma", "Sales Manager", "manager", "confirmed", date(2022, 6, 1), "amit@demo3", 3, 0, 10),
    ("E1004", "Neha Kapoor", "HR Manager", "hr_admin", "confirmed", date(2021, 3, 10), "neha@demo4", 1, 4, 5),
]


def main() -> None:
    year = date.today().year
    with _connect() as conn:
        conn.execute(SCHEMA)
        for emp_id, name, title, role, status, joined, password, cl, sl, el in DEMO_USERS:
            conn.execute(
                """
                INSERT INTO hr_employees
                    (employee_id, full_name, designation, role, status, joined_on, password_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (employee_id) DO UPDATE SET
                    full_name = EXCLUDED.full_name, designation = EXCLUDED.designation,
                    role = EXCLUDED.role, status = EXCLUDED.status,
                    joined_on = EXCLUDED.joined_on, password_hash = EXCLUDED.password_hash
                """,
                (emp_id, name, title, role, status, joined, hash_password(password)),
            )
            conn.execute(
                """
                INSERT INTO hr_leave_usage (employee_id, year, cl_used, sl_used, el_used)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (employee_id, year) DO UPDATE SET
                    cl_used = EXCLUDED.cl_used, sl_used = EXCLUDED.sl_used, el_used = EXCLUDED.el_used
                """,
                (emp_id, year, cl, sl, el),
            )
    print(f"Seeded {len(DEMO_USERS)} demo employees for {year}.\n")
    print("Demo logins (employee ID / password / role):")
    for emp_id, name, _t, role, status, _j, password, *_ in DEMO_USERS:
        print(f"  {emp_id} / {password:<12} {role:<9} {status:<10} {name}")


if __name__ == "__main__":
    main()
