import re

import psycopg
from fastapi import APIRouter, Depends, Request, Response

from ..auth import require_role
from ..db import pool
from ..errors import HttpError
from ..rate_limit import api_rate_limit
from ..validate import parse_id, validate_search

router = APIRouter(dependencies=[Depends(api_rate_limit)])


@router.get("/products")
def search_products(request: Request):
    # ?search=a&search=b (lặp tham số) bị coi là không hợp lệ thay vì lấy bừa một giá trị
    values = request.query_params.getlist("search")
    search = validate_search(None if not values else values[0] if len(values) == 1 else values)

    # SỬA #2: prepared statement. Câu lệnh và dữ liệu đi riêng, nên dữ liệu không bao giờ thành lệnh SQL.
    # Escape ký tự đại diện của LIKE (\ % _) để từ khóa được hiểu là chữ thường.
    pattern = "%" + re.sub(r"([\\%_])", r"\\\1", search) + "%"
    with pool.connection() as conn:
        return conn.execute(
            "SELECT id, name, description, price, stock FROM products WHERE name ILIKE %s ORDER BY id",
            (pattern,),
        ).fetchall()


# SỬA #1a: phân quyền tầng 1 - chỉ admin được xóa sản phẩm.
# require_role('admin') tự gọi authenticate trước (401 nếu chưa đăng nhập), rồi mới kiểm tra vai trò (403).
@router.delete(
    "/products/{product_id}", status_code=204, dependencies=[Depends(require_role("admin"))]
)
def delete_product(product_id: str):
    pid = parse_id(product_id)
    try:
        with pool.connection() as conn:
            result = conn.execute("DELETE FROM products WHERE id = %s", (pid,))
            if result.rowcount == 0:
                raise HttpError(404, "Không tìm thấy sản phẩm")
    except psycopg.errors.ForeignKeyViolation:
        raise HttpError(409, "Sản phẩm đã có trong đơn hàng nên không thể xóa")
    return Response(status_code=204)
