from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Body, Depends

from ..auth import CurrentUser, authenticate
from ..db import pool
from ..errors import HttpError
from ..rate_limit import api_rate_limit
from ..validate import parse_id, validate_comment, validate_order_input

router = APIRouter(dependencies=[Depends(api_rate_limit)])


# SỬA #1b - Phân quyền tầng 2: đối chiếu chủ của đơn hàng với người đang gọi.
# Chỉ chủ đơn hoặc admin được truy cập. (Một số hệ thống trả 404 thay vì 403 để không lộ
# việc đơn hàng có tồn tại; ở đây dùng 403 cho khớp phần lý thuyết.)
def load_order_for_user(conn, order_id: int, user: CurrentUser) -> dict:
    order = conn.execute("SELECT * FROM orders WHERE id = %s", (order_id,)).fetchone()
    if order is None:
        raise HttpError(404, "Không tìm thấy đơn hàng")
    if order["user_id"] != user.id and user.role != "admin":
        raise HttpError(403, "Forbidden")
    return order


@router.get("/orders")
def list_orders(user: CurrentUser = Depends(authenticate)):
    with pool.connection() as conn:
        if user.role == "admin":
            return conn.execute("SELECT * FROM orders ORDER BY id").fetchall()
        return conn.execute(
            "SELECT * FROM orders WHERE user_id = %s ORDER BY id", (user.id,)
        ).fetchall()


# Đặt hàng: toàn bộ nằm trong MỘT giao dịch (hoặc thành công hết, hoặc hủy hết)
@router.post("/orders", status_code=201)
def create_order(body: Any = Body(None), user: CurrentUser = Depends(authenticate)):
    # SỬA #9: kiểm tra đầu vào trước khi chạm vào database
    data = validate_order_input(body)

    # Thoát khối "with conn.transaction()" bằng lỗi thì giao dịch tự ROLLBACK; thoát bình thường thì COMMIT
    with pool.connection() as conn, conn.transaction():
        total = Decimal(0)
        lines = []
        # Khóa các dòng sản phẩm theo thứ tự id tăng dần để tránh deadlock giữa hai đơn đặt cùng lúc
        for item in sorted(data["items"], key=lambda i: i["productId"]):
            # FOR UPDATE: khóa dòng để hai khách không cùng mua món cuối cùng
            product = conn.execute(
                "SELECT id, price, stock FROM products WHERE id = %s FOR UPDATE",
                (item["productId"],),
            ).fetchone()
            if product is None:
                raise HttpError(404, f"Sản phẩm {item['productId']} không tồn tại")
            if product["stock"] < item["quantity"]:
                raise HttpError(409, f"Sản phẩm {product['id']} không đủ hàng")
            conn.execute(
                "UPDATE products SET stock = stock - %s WHERE id = %s",
                (item["quantity"], product["id"]),
            )
            # Giá lấy từ database, không tin giá do client gửi. Tính bằng Decimal nên không sai số tiền lẻ.
            total += Decimal(product["price"]) * item["quantity"]
            lines.append((product["id"], item["quantity"], product["price"]))

        order = conn.execute(
            "INSERT INTO orders (user_id, total, shipping_address) VALUES (%s, %s, %s) RETURNING *",
            (user.id, total, data["shippingAddress"]),
        ).fetchone()
        for product_id, quantity, unit_price in lines:
            conn.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price) "
                "VALUES (%s, %s, %s, %s)",
                (order["id"], product_id, quantity, unit_price),
            )
    return order


@router.get("/orders/{order_id}")
def get_order(order_id: str, user: CurrentUser = Depends(authenticate)):
    with pool.connection() as conn:
        order = load_order_for_user(conn, parse_id(order_id), user)
        items = conn.execute(
            "SELECT product_id, quantity, unit_price FROM order_items WHERE order_id = %s ORDER BY id",
            (order["id"],),
        ).fetchall()
    return {**order, "items": items}


@router.post("/orders/{order_id}/reviews", status_code=201)
def create_review(order_id: str, body: Any = Body(None), user: CurrentUser = Depends(authenticate)):
    with pool.connection() as conn:
        order = load_order_for_user(conn, parse_id(order_id), user)
        # Dữ liệu lưu nguyên văn; việc chống XSS làm ở nơi hiển thị (escape) và bằng CSP
        comment = validate_comment(body)
        return conn.execute(
            "INSERT INTO reviews (order_id, user_id, comment) VALUES (%s, %s, %s) RETURNING *",
            (order["id"], user.id, comment),
        ).fetchone()


@router.get("/orders/{order_id}/reviews")
def list_reviews(order_id: str, user: CurrentUser = Depends(authenticate)):
    with pool.connection() as conn:
        order = load_order_for_user(conn, parse_id(order_id), user)
        return conn.execute(
            """SELECT r.id, r.comment, r.created_at, u.email
                 FROM reviews r JOIN users u ON u.id = r.user_id
                WHERE r.order_id = %s ORDER BY r.id""",
            (order["id"],),
        ).fetchall()
