from fastapi import APIRouter, Depends, Response

from ..auth import authenticate
from ..db import pool
from ..errors import HttpError

router = APIRouter()


# Tìm sản phẩm theo từ khóa (công khai)
@router.get("/products")
def search_products(search: str = ""):
    # LỖI #2: SQL Injection - nối chuỗi trực tiếp vào câu truy vấn.
    # Dữ liệu người dùng nhập trở thành một phần của câu lệnh SQL.
    sql = (
        "SELECT id, name, description, price, stock FROM products WHERE name ILIKE '%"
        + search
        + "%' ORDER BY id"
    )
    with pool.connection() as conn:
        return conn.execute(sql).fetchall()


# LỖI #1a: thiếu dependency kiểm tra vai trò (tầng 1 của phân quyền).
# Chỉ có Depends(authenticate): đăng nhập là xóa được sản phẩm, kể cả khách hàng.
@router.delete("/products/{product_id}", status_code=204, dependencies=[Depends(authenticate)])
def delete_product(product_id: str):
    with pool.connection() as conn:
        result = conn.execute("DELETE FROM products WHERE id = %s", (product_id,))
        if result.rowcount == 0:
            raise HttpError(404, "Không tìm thấy sản phẩm")
    return Response(status_code=204)
