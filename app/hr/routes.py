"""Login endpoint and the `get_current_user` dependency for protected routes."""

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.hr import auth, repository

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)
_dummy_hash: str | None = None


def _secret() -> str:
    from app.config import settings

    return settings.JWT_SECRET


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=401, detail=detail, headers={"WWW-Authenticate": "Bearer"})


class LoginRequest(BaseModel):
    employee_id: str
    password: str


@router.post("/login")
def login(body: LoginRequest):
    """Exchange employee ID + password for a short-lived access token."""
    global _dummy_hash
    employee = repository.get_employee(body.employee_id.strip().upper())

    if employee is None:
        # Spend the same time as a real check so response timing doesn't reveal valid IDs.
        _dummy_hash = _dummy_hash or auth.hash_password("not-a-real-password")
        auth.verify_password(body.password, _dummy_hash)
        raise _unauthorized("Invalid employee ID or password")

    if not auth.verify_password(body.password, employee["password_hash"]):
        raise _unauthorized("Invalid employee ID or password")

    token = auth.create_access_token(employee["employee_id"], employee["role"], _secret())
    return {
        "access_token": token,
        "token_type": "bearer",
        "employee_id": employee["employee_id"],
        "name": employee["full_name"],
        "role": employee["role"],
    }


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """Identify the caller from the bearer token. Never trusts names typed in chat."""
    if credentials is None:
        raise _unauthorized("Not authenticated")
    try:
        claims = auth.decode_access_token(credentials.credentials, _secret())
    except jwt.InvalidTokenError:
        raise _unauthorized("Invalid or expired token") from None

    employee = repository.get_employee(claims["sub"])
    if employee is None:
        raise _unauthorized("Unknown user")
    employee = dict(employee)
    employee.pop("password_hash", None)
    return employee
