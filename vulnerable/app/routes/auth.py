from typing import Any

import bcrypt
from fastapi import APIRouter, Body

from ..auth import sign_token
from ..db import pool
from ..errors import HttpError

router = APIRouter()


@router.post("/register", status_code=201)
def register(body: Any = Body(None)):
    # LỖI #9: không kiểm tra định dạng email, độ dài mật khẩu
    email, password = body["email"], body["password"]
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(12)).decode("ascii")
    with pool.connection() as conn:
        return conn.execute(
            "INSERT INTO users (email, password_hash, role) VALUES (%s, %s, 'customer') "
            "RETURNING id, email, role",
            (email, hashed),
        ).fetchone()


@router.post("/login")
def login(body: Any = Body(None)):
    email, password = body["email"], body["password"]
    with pool.connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE email = %s", (email,)).fetchone()

    # LỖI #4c: thông báo khác nhau cho "sai email" và "sai mật khẩu" -> kẻ xấu dò được email nào đã đăng ký
    if user is None:
        raise HttpError(401, "Email không tồn tại")

    if not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("ascii")):
        raise HttpError(401, "Sai mật khẩu")

    return {"token": sign_token(user["id"], user["role"])}
