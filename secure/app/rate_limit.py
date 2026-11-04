"""SỬA #5: giới hạn số request.

Bộ đếm lưu trong bộ nhớ của tiến trình; khi chạy nhiều server (hoặc nhiều worker) cần kho dùng chung
như Redis. Nếu đặt sau reverse proxy (Nginx), phải cho uvicorn tin header X-Forwarded-For
(--forwarded-allow-ips) để lấy đúng IP của client.
"""
import math
import threading
import time
from collections.abc import Callable

from fastapi import Request

from .config import settings
from .errors import HttpError


class FixedWindowCounter:
    """Đếm số lần xảy ra theo từng khóa (IP) trong một cửa sổ thời gian cố định."""

    _PURGE_ABOVE = 10_000  # quá ngưỡng này thì dọn các khóa đã hết hạn để bộ nhớ không phình mãi

    def __init__(
        self, window_seconds: float, limit: int, clock: Callable[[], float] = time.monotonic
    ):
        self.window = window_seconds
        self.limit = limit
        self._clock = clock
        self._entries: dict[str, tuple[float, int]] = {}  # khóa -> (thời điểm hết cửa sổ, số lần)
        self._lock = threading.Lock()  # endpoint đồng bộ chạy trên nhiều luồng

    def count(self, key: str) -> int:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None or entry[0] <= self._clock():
                return 0
            return entry[1]

    def hit(self, key: str) -> int:
        """Ghi nhận một lần, trả về tổng số lần trong cửa sổ hiện tại."""
        with self._lock:
            now = self._clock()
            if len(self._entries) > self._PURGE_ABOVE:
                self._entries = {k: v for k, v in self._entries.items() if v[0] > now}
            entry = self._entries.get(key)
            reset_at, count = (now + self.window, 0) if entry is None or entry[0] <= now else entry
            self._entries[key] = (reset_at, count + 1)
            return count + 1

    def retry_after(self, key: str) -> int:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return 1
            return max(1, math.ceil(entry[0] - self._clock()))

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


# Rộng cho toàn bộ API: 100 request / phút / IP
api_limiter = FixedWindowCounter(window_seconds=60, limit=100)
# Chặt cho /login: chỉ đếm các lần THẤT BẠI, đủ ngưỡng thì các lần sau trả 429
login_failures = FixedWindowCounter(window_seconds=15 * 60, limit=settings.login_rate_max)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def api_rate_limit(request: Request) -> None:
    """Dependency gắn cho mọi router API."""
    ip = client_ip(request)
    if api_limiter.hit(ip) > api_limiter.limit:
        raise HttpError(
            429,
            "Quá nhiều yêu cầu, vui lòng thử lại sau",
            {"Retry-After": str(api_limiter.retry_after(ip))},
        )


def login_rate_limit(request: Request) -> None:
    """Dependency của /login: chặn khi IP đã đăng nhập sai quá nhiều lần."""
    ip = client_ip(request)
    if login_failures.count(ip) >= login_failures.limit:
        raise HttpError(
            429,
            "Quá nhiều lần đăng nhập sai, vui lòng thử lại sau",
            {"Retry-After": str(login_failures.retry_after(ip))},
        )


def record_login_failure(request: Request) -> None:
    login_failures.hit(client_ip(request))


def reset_rate_limits() -> None:
    api_limiter.clear()
    login_failures.clear()
