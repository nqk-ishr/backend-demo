import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import pool
from .errors import register_error_handlers
from .middleware import BodySizeLimitMiddleware, CatchAllErrorsMiddleware, SecurityHeadersMiddleware
from .routes import auth as auth_routes
from .routes import orders as order_routes
from .routes import products as product_routes

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("shop")

PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open(wait=True, timeout=30)
    log.info("[SECURE] sẵn sàng")
    yield
    pool.close()


# Tắt /docs, /redoc, /openapi.json: CSP chặn Swagger UI tải script từ CDN, và bản chạy thật
# không nên công khai tài liệu API tự sinh.
app = FastAPI(title="Shop API", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
register_error_handlers(app)

# Thứ tự bên dưới: lớp thêm SAU nằm NGOÀI cùng. Một request đi từ ngoài vào trong:
# header bảo mật -> CORS -> giới hạn body -> bắt lỗi -> router.
app.add_middleware(CatchAllErrorsMiddleware)  # SỬA #7
app.add_middleware(BodySizeLimitMiddleware, max_bytes=10 * 1024)
# SỬA #6: chỉ các origin trong danh sách mới được gọi API từ trình duyệt
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(SecurityHeadersMiddleware)  # SỬA #3


@app.get("/health")
def health():
    return {"ok": True, "version": "secure"}


app.include_router(auth_routes.router)
app.include_router(product_routes.router)
app.include_router(order_routes.router)

# Phục vụ frontend tĩnh. Đặt cuối cùng để các route API ở trên được ưu tiên.
app.mount("/", StaticFiles(directory=PUBLIC_DIR, html=True), name="public")
