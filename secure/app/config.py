"""SỬA #4a: secret đọc từ biến môi trường, thiếu hoặc quá yếu thì KHÔNG khởi động."""
import os
from collections.abc import Mapping
from dataclasses import dataclass


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Config:
    jwt_secret: str
    database_url: str
    # SỬA #6: danh sách origin được phép gọi API từ trình duyệt
    cors_origins: list[str]
    login_rate_max: int
    bcrypt_cost: int = 12


def _required(env: Mapping[str, str], name: str) -> str:
    value = env.get(name)
    if not value:
        raise ConfigError(f"Thiếu biến môi trường {name}")
    return value


def load_config(env: Mapping[str, str]) -> Config:
    jwt_secret = _required(env, "JWT_SECRET")
    if len(jwt_secret) < 32:
        raise ConfigError("JWT_SECRET phải dài ít nhất 32 ký tự")

    try:
        login_rate_max = int(env.get("LOGIN_RATE_LIMIT_MAX", "5"))
    except ValueError:
        raise ConfigError("LOGIN_RATE_LIMIT_MAX phải là số nguyên")

    origins = env.get("CORS_ORIGINS", "http://localhost:3002").split(",")
    return Config(
        jwt_secret=jwt_secret,
        database_url=_required(env, "DATABASE_URL"),
        cors_origins=[o.strip() for o in origins if o.strip()],
        login_rate_max=login_rate_max,
    )


# Đọc cấu hình ngay khi import: thiếu hoặc yếu thì ứng dụng dừng ở đây, không chạy với cấu hình hở.
settings = load_config(os.environ)
