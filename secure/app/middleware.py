"""Ba lớp bảo vệ nằm ngoài các route, viết dạng ASGI thuần để áp dụng cho MỌI phản hồi."""
import logging

from fastapi import HTTPException
from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse

log = logging.getLogger("shop")

# SỬA #3: Content-Security-Policy (chỉ chạy script từ chính website) cùng các header bảo mật
# thường gặp, tương đương những gì helmet bật sẵn bên Express.
# Bỏ upgrade-insecure-requests vì demo chạy trên http://localhost, không có HTTPS.
CSP = "; ".join(
    [
        "default-src 'self'",
        "base-uri 'self'",
        "font-src 'self' https: data:",
        "form-action 'self'",
        "frame-ancestors 'self'",
        "img-src 'self' data:",
        "object-src 'none'",
        "script-src 'self'",
        "script-src-attr 'none'",
        "style-src 'self' https: 'unsafe-inline'",
    ]
)

SECURITY_HEADERS = {
    "Content-Security-Policy": CSP,
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=15552000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
}


class SecurityHeadersMiddleware:
    """SỬA #3: gắn header bảo mật vào mọi phản hồi (kể cả lỗi và file tĩnh)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS.items():
                    headers[name] = value
            await send(message)

        await self.app(scope, receive, send_with_headers)


class PayloadTooLarge(HTTPException):
    def __init__(self):
        super().__init__(status_code=413, detail="Dữ liệu quá lớn")


class BodySizeLimitMiddleware:
    """Giới hạn kích thước body (Starlette không có sẵn). Đếm theo số byte thực nhận, không tin Content-Length."""

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise PayloadTooLarge()  # được đổi thành phản hồi 413 ở errors.py
            return message

        await self.app(scope, limited_receive, send)


class CatchAllErrorsMiddleware:
    """SỬA #7: lỗi bất ngờ chỉ ghi vào log nội bộ, người gọi chỉ nhận thông báo chung.

    Đặt BÊN TRONG lớp CORS để phản hồi 500 vẫn mang header CORS.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        started = False

        async def tracking_send(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, tracking_send)
        except Exception:
            log.exception("Lỗi chưa được xử lý")
            if started:  # đã gửi một phần phản hồi thì không thể đổi thành 500
                raise
            response = JSONResponse({"error": "Lỗi máy chủ"}, status_code=500)
            await response(scope, receive, send)
