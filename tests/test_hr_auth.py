import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.hr import auth, routes

SECRET = "x" * 48
FAKE_DB = {}


@pytest.fixture()
def client(monkeypatch):
    FAKE_DB.clear()
    FAKE_DB["E1001"] = {
        "employee_id": "E1001",
        "full_name": "Rahul Sharma",
        "designation": "Sales Executive",
        "role": "employee",
        "status": "confirmed",
        "joined_on": "2024-01-15",
        "password_hash": auth.hash_password("rahul@demo1", iterations=1000),
    }
    monkeypatch.setattr(routes, "_secret", lambda: SECRET)
    monkeypatch.setattr(routes.repository, "get_employee", lambda emp_id: FAKE_DB.get(emp_id))

    app = FastAPI()
    app.include_router(routes.router)

    @app.get("/me")
    def me(user=Depends(routes.get_current_user)):
        return user

    return TestClient(app)


# ---- passwords ----------------------------------------------------------
def test_password_roundtrip_and_salting():
    h1 = auth.hash_password("secret-1", iterations=1000)
    h2 = auth.hash_password("secret-1", iterations=1000)
    assert h1 != h2  # different salts
    assert auth.verify_password("secret-1", h1)
    assert not auth.verify_password("secret-2", h1)


@pytest.mark.parametrize("garbage", ["", "plain", "a$b$c$d", "pbkdf2_sha256$x$zz$zz", None])
def test_verify_rejects_malformed_hash(garbage):
    assert auth.verify_password("anything", garbage) is False


# ---- tokens -------------------------------------------------------------
def test_token_roundtrip():
    token = auth.create_access_token("E1001", "employee", SECRET)
    claims = auth.decode_access_token(token, SECRET)
    assert claims["sub"] == "E1001" and claims["role"] == "employee"


def test_expired_token_rejected():
    token = auth.create_access_token("E1001", "employee", SECRET, minutes=1, now=1_000_000)
    with pytest.raises(jwt.ExpiredSignatureError):
        auth.decode_access_token(token, SECRET)


def test_token_with_wrong_secret_rejected():
    token = auth.create_access_token("E1001", "employee", SECRET)
    with pytest.raises(jwt.InvalidTokenError):
        auth.decode_access_token(token, "y" * 48)


# ---- endpoints ----------------------------------------------------------
def test_login_success_then_me(client):
    r = client.post("/login", json={"employee_id": "e1001", "password": "rahul@demo1"})
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Rahul Sharma" and body["role"] == "employee"

    me = client.get("/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["employee_id"] == "E1001"
    assert "password_hash" not in me.json()


def test_login_wrong_password_and_unknown_user_look_identical(client):
    wrong = client.post("/login", json={"employee_id": "E1001", "password": "nope"})
    unknown = client.post("/login", json={"employee_id": "E9999", "password": "nope"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_me_requires_a_valid_token(client):
    assert client.get("/me").status_code == 401
    assert client.get("/me", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_token_for_deleted_user_is_rejected(client):
    token = auth.create_access_token("E1001", "employee", SECRET)
    FAKE_DB.clear()
    r = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
