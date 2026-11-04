import os

# Phải đặt TRƯỚC khi import app: app.config đọc môi trường ngay lúc import.
os.environ["JWT_SECRET"] = "x" * 40
os.environ["DATABASE_URL"] = "postgres://user:pass@localhost:5432/shop"
os.environ["CORS_ORIGINS"] = "http://localhost:3002"
os.environ["LOGIN_RATE_LIMIT_MAX"] = "5"

import pytest  # noqa: E402

from app.rate_limit import reset_rate_limits  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    reset_rate_limits()
    yield
    reset_rate_limits()
