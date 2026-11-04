import warnings
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth import (
    CurrentUser,
    authenticate,
    hash_password,
    require_role,
    sign_token,
    verify_password,
)
from app.config import settings
from app.errors import register_error_handlers

# Ứng dụng nhỏ chỉ để thử riêng phần xác thực và phân quyền tầng 1 (không cần database)
mini = FastAPI()
register_error_handlers(mini)


@mini.get("/me")
def me(user: CurrentUser = Depends(authenticate)):
    return {"id": user.id, "role": user.role}


@mini.get("/admin", dependencies=[Depends(require_role("admin"))])
def admin_only():
    return {"ok": True}


client = TestClient(mini)


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def forge(payload, key, algorithm="HS256"):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # khóa ngắn làm PyJWT cảnh báo; đó chính là điều ta đang thử
        return jwt.encode(payload, key, algorithm=algorithm)


def test_token_contains_id_role_and_expiry():
    payload = jwt.decode(sign_token(7, "customer"), options={"verify_signature": False})
    assert payload["sub"] == "7"
    assert payload["role"] == "customer"
    assert payload["exp"] > payload["iat"], "token phải có thời điểm hết hạn"


def test_authenticate_accepts_valid_token_and_returns_user():
    res = client.get("/me", headers=bearer(sign_token(7, "admin")))
    assert res.status_code == 200
    assert res.json() == {"id": 7, "role": "admin"}


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer abc.def.ghi"}, {"Authorization": "abc"}])
def test_authenticate_returns_401_for_missing_or_bad_token(headers):
    assert client.get("/me", headers=headers).status_code == 401


def test_token_signed_with_other_secret_is_rejected():
    forged = forge({"sub": "1", "role": "admin", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, "secret")
    assert client.get("/me", headers=bearer(forged)).status_code == 401


def test_expired_token_is_rejected():
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    expired = jwt.encode({"sub": "1", "role": "admin", "exp": past}, settings.jwt_secret, algorithm="HS256")
    assert client.get("/me", headers=bearer(expired)).status_code == 401


def test_token_without_expiry_is_rejected():
    no_exp = jwt.encode({"sub": "1", "role": "admin"}, settings.jwt_secret, algorithm="HS256")
    assert client.get("/me", headers=bearer(no_exp)).status_code == 401


def test_unsigned_token_with_alg_none_is_rejected():
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    unsigned = jwt.encode({"sub": "1", "role": "admin", "exp": future}, None, algorithm="none")
    assert client.get("/me", headers=bearer(unsigned)).status_code == 401


def test_require_role_blocks_customer_with_403_and_lets_admin_through():
    assert client.get("/admin", headers=bearer(sign_token(2, "customer"))).status_code == 403
    assert client.get("/admin", headers=bearer(sign_token(1, "admin"))).status_code == 200


def test_require_role_checks_authentication_first():
    # Chưa đăng nhập: 401 (chưa biết là ai), không phải 403
    assert client.get("/admin").status_code == 401


def test_password_hashing_roundtrip():
    hashed = hash_password("Abcdefg1")
    assert hashed.startswith("$2") and "Abcdefg1" not in hashed
    assert verify_password("Abcdefg1", hashed) is True
    assert verify_password("sai-mat-khau", hashed) is False


def test_verify_password_does_not_crash_on_overlong_password():
    assert verify_password("x" * 100, hash_password("Abcdefg1")) is False
