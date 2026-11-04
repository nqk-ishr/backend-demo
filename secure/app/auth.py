from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, Request

from .config import settings
from .errors import HttpError


@dataclass(frozen=True)
class CurrentUser:
    """Danh tính rút ra từ token: thứ mà bước xác thực để lại cho các bước sau."""

    id: int
    role: str


def hash_password(plain: str) -> str:
    # Băm bằng bcrypt (tự sinh salt, cost = 12). Không lưu mật khẩu gốc.
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(settings.bcrypt_cost)).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("ascii"))
    except ValueError:
        # bcrypt từ chối mật khẩu dài hơn 72 byte; mật khẩu đã đăng ký luôn <= 72 byte nên coi là không khớp
        return False


def sign_token(user_id: int, role: str) -> str:
    # SỬA #4b: token hết hạn sau 15 phút, chỉ định rõ thuật toán ký.
    # (Mở rộng cho nhóm: thêm refresh token để cấp token mới mà không bắt đăng nhập lại.)
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),  # theo chuẩn JWT, "sub" là chuỗi
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=15),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def authenticate(request: Request) -> CurrentUser:
    """Xác thực: kiểm tra chữ ký, hạn dùng và thuật toán, rồi trả về danh tính.

    Đây là phần việc mà Express gọi là middleware; trong FastAPI nó là một dependency
    gắn theo từng route: Depends(authenticate). Sai thì ném HttpError 401 và handler không chạy.
    """
    header = request.headers.get("authorization", "")
    token = header[7:] if header.startswith("Bearer ") else None
    if not token:
        raise HttpError(401, "Thiếu token")
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],  # chỉ nhận đúng thuật toán đã dùng để ký
            options={"require": ["exp", "sub"]},  # token không có hạn dùng bị từ chối
        )
        return CurrentUser(id=int(payload["sub"]), role=str(payload["role"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HttpError(401, "Token không hợp lệ hoặc đã hết hạn")


def require_role(*roles: str):
    """SỬA #1a - Phân quyền tầng 1: kiểm tra vai trò trước khi vào handler.

    Role nằm trong token nên có thể cũ nếu quyền vừa bị đổi; với thao tác rất nhạy cảm
    (đổi quyền, thanh toán) nên tra lại role trong database.
    """

    def checker(user: CurrentUser = Depends(authenticate)) -> CurrentUser:
        if user.role not in roles:
            raise HttpError(403, "Forbidden")
        return user

    return checker
