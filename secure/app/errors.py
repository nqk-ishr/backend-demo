from collections.abc import Mapping

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class HttpError(Exception):
    """Lỗi kèm mã HTTP: handler ném ra, người gọi chỉ nhận {"error": message}."""

    def __init__(self, status: int, message: str, headers: Mapping[str, str] | None = None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.headers = headers


# Thông báo cho các lỗi do chính FastAPI/Starlette sinh ra (không dùng nguyên văn tiếng Anh của chúng)
_STATUS_MESSAGES = {
    404: "Không tìm thấy",
    405: "Phương thức không được hỗ trợ",
    413: "Dữ liệu quá lớn",
}


def register_error_handlers(app: FastAPI) -> None:
    """SỬA #7: người gọi chỉ nhận thông báo chung dạng {"error": ...}; chi tiết chỉ nằm trong log."""

    @app.exception_handler(HttpError)
    async def http_error(request, exc: HttpError):
        return JSONResponse({"error": exc.message}, status_code=exc.status, headers=exc.headers)

    @app.exception_handler(StarletteHTTPException)
    async def framework_http_error(request, exc: StarletteHTTPException):
        message = _STATUS_MESSAGES.get(exc.status_code, "Yêu cầu không hợp lệ")
        return JSONResponse(
            {"error": message}, status_code=exc.status_code, headers=getattr(exc, "headers", None)
        )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc: RequestValidationError):
        if any(err.get("type") == "json_invalid" for err in exc.errors()):
            return JSONResponse({"error": "JSON không hợp lệ"}, status_code=400)
        return JSONResponse({"error": "Dữ liệu gửi lên không hợp lệ"}, status_code=400)
