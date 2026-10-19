"""Database access for demo employees and leave usage (Neon Postgres).

Tables are prefixed `hr_` so they never clash with the LangGraph checkpoint tables.
Imports are lazy so the pure-logic modules can be tested without a database.
"""

from datetime import date
from typing import Any


def _connect():
    import psycopg
    from psycopg.rows import dict_row

    from app.config import settings

    return psycopg.connect(settings.NEON_DB_URL, row_factory=dict_row)


def get_employee(employee_id: str) -> dict[str, Any] | None:
    """Return one employee row (including password_hash) or None."""
    with _connect() as conn:
        return conn.execute(
            """
            SELECT employee_id, full_name, designation, role, status, joined_on, password_hash
            FROM hr_employees
            WHERE employee_id = %s
            """,
            (employee_id,),
        ).fetchone()


def get_leave_usage(employee_id: str, year: int | None = None) -> dict[str, Any]:
    """Casual/sick days used in `year`, and Earned Leave used across all years."""
    year = year or date.today().year
    with _connect() as conn:
        this_year = conn.execute(
            "SELECT cl_used, sl_used FROM hr_leave_usage WHERE employee_id = %s AND year = %s",
            (employee_id, year),
        ).fetchone()
        el_total = conn.execute(
            "SELECT COALESCE(SUM(el_used), 0) AS el_used FROM hr_leave_usage WHERE employee_id = %s",
            (employee_id,),
        ).fetchone()
    return {
        "cl_used": this_year["cl_used"] if this_year else 0,
        "sl_used": this_year["sl_used"] if this_year else 0,
        "el_used": el_total["el_used"] if el_total else 0,
    }
