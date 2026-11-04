import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .db import pool
from .errors import HttpError
from .routes import auth as auth_routes
from .routes import orders as order_routes
from .routes import products as product_routes

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("shop")

PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open(wait=True, timeout=30)
    log.info("[VULNERABLE] sẵn sàng")
    yield
    pool.close()


# Trang /docs (Swagger UI) của FastAPI để bật sẵn cho tiện thử tay; chỉ chạy local.
app = FastAPI(title="Shop API - BẢN CÓ LỖI", lifespan=lifespan)


# LỖI #7: trả nguyên thông báo lỗi nội bộ (kể cả lỗi SQL) cho người gọi.
# Đặt middleware này TRƯỚC CORS để phản hồi lỗi vẫn mang header CORS.
@app.middleware("http")
async def leak_internal_errors(request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        log.exception("Lỗi chưa được xử lý")
        return JSONResponse(
            {"error": str(exc), "code": getattr(exc, "sqlstate", None)}, status_code=500
        )


# LỖI #6: cho phép MỌI website gọi API từ trình duyệt (Access-Control-Allow-Origin: *)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# LỖI #5: không có rate limiting ở bất kỳ endpoint nào
# LỖI #3: không có header Content-Security-Policy


@app.exception_handler(HttpError)
async def http_error_handler(request, exc: HttpError):
    return JSONResponse({"error": exc.message}, status_code=exc.status)


@app.exception_handler(StarletteHTTPException)
async def starlette_http_error_handler(request, exc: StarletteHTTPException):
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc: RequestValidationError):
    return JSONResponse({"error": "JSON không hợp lệ"}, status_code=400)


@app.get("/health")
def health():
    return {"ok": True, "version": "vulnerable"}


app.include_router(auth_routes.router)
app.include_router(product_routes.router)
app.include_router(order_routes.router)

# Phục vụ frontend tĩnh. Đặt cuối cùng để các route API ở trên được ưu tiên.
app.mount("/", StaticFiles(directory=PUBLIC_DIR, html=True), name="public")
