import os
from dataclasses import dataclass

import jwt
from fastapi import Request

from .errors import HttpError

# LỖI #4a: secret viết cứng trong code, có giá trị mặc định yếu.
# Nếu secret bị đoán ra, kẻ xấu tự tạo token role "admin".
JWT_SECRET = os.environ.get("JWT_SECRET", "secret")


@dataclass(frozen=True)
class CurrentUser:
    """Danh tính rút ra từ token: thứ mà middleware xác thực để lại cho các bước sau."""

    id: int
    role: str


def sign_token(user_id: int, role: str) -> str:
    # LỖI #4b: token KHÔNG có hạn dùng (thiếu claim "exp") -> bị đánh cắp là dùng mãi mãi
    return jwt.encode({"sub": str(user_id), "role": role}, JWT_SECRET, algorithm="HS256")


def authenticate(request: Request) -> CurrentUser:
    """Xác thực: kiểm tra token, trả về danh tính.

    Dùng như middleware theo từng route: Depends(authenticate).
    Sai thì ném HttpError 401 và handler không bao giờ chạy.
    """
    header = request.headers.get("authorization", "")
    token = header[7:] if header.startswith("Bearer ") else None
    if not token:
        raise HttpError(401, "Thiếu token")
    try:
        # verify_sub=False: chấp nhận cả token tự tạo với "sub" là số (đúng kiểu kẻ tấn công hay làm)
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"], options={"verify_sub": False})
        return CurrentUser(id=int(payload["sub"]), role=str(payload["role"]))
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        raise HttpError(401, "Token không hợp lệ")
