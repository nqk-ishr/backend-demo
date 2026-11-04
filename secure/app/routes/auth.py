from typing import Any

import psycopg
from fastapi import APIRouter, Body, Depends, Request

from ..auth import hash_password, sign_token, verify_password
from ..db import pool
from ..errors import HttpError
from ..rate_limit import api_rate_limit, login_rate_limit, record_login_failure
from ..validate import is_email, is_password

router = APIRouter(dependencies=[Depends(api_rate_limit)])

# Dùng khi email không tồn tại, để thời gian phản hồi giống trường hợp sai mật khẩu
DUMMY_HASH = hash_password("mat-khau-gia-de-so-sanh")
LOGIN_ERROR = "Email hoặc mật khẩu không đúng"


@router.post("/register", status_code=201)
def register(body: Any = Body(None)):
    data = body if isinstance(body, dict) else {}
    email, password = data.get("email"), data.get("password")
    if not is_email(email):
        raise HttpError(400, "Email không hợp lệ")
    if not is_password(password):
        raise HttpError(400, "Mật khẩu phải có từ 8 ký tự và tối đa 72 byte")

    hashed = hash_password(password)
    try:
        with pool.connection() as conn:
            return conn.execute(
                "INSERT INTO users (email, password_hash, role) VALUES (%s, %s, 'customer') "
                "RETURNING id, email, role",
                (email.lower(), hashed),
            ).fetchone()
    except psycopg.errors.UniqueViolation:
        raise HttpError(409, "Email đã được đăng ký")


# SỬA #5: login_rate_limit chặn dò mật khẩu
@router.post("/login", dependencies=[Depends(login_rate_limit)])
def login(request: Request, body: Any = Body(None)):
    data = body if isinstance(body, dict) else {}
    email, password = data.get("email"), data.get("password")
    if not is_email(email) or not isinstance(password, str):
        record_login_failure(request)
        raise HttpError(401, LOGIN_ERROR)

    with pool.connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE email = %s", (email.lower(),)).fetchone()

    # SỬA #4c: luôn so sánh hash và luôn trả CÙNG một thông báo, không lộ email nào đã đăng ký
    ok = verify_password(password, user["password_hash"] if user else DUMMY_HASH)
    if user is None or not ok:
        record_login_failure(request)
        raise HttpError(401, LOGIN_ERROR)

    return {"token": sign_token(user["id"], user["role"])}
