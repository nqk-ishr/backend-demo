from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Body, Depends

from ..auth import CurrentUser, authenticate
from ..db import pool
from ..errors import HttpError

router = APIRouter()


# Danh sách đơn: khách thấy đơn của mình, admin thấy tất cả
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
    # LỖI #9: không kiểm tra đầu vào (items, quantity, shippingAddress)
    items, shipping_address = body["items"], body["shippingAddress"]

    # Thoát khối "with conn.transaction()" bằng lỗi thì giao dịch tự ROLLBACK; thoát bình thường thì COMMIT
    with pool.connection() as conn, conn.transaction():
        total = Decimal(0)
        lines = []
        # Khóa các dòng sản phẩm theo thứ tự id tăng dần để tránh deadlock giữa hai đơn đặt cùng lúc
        for item in sorted(items, key=lambda i: i["productId"]):
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
            # Giá lấy từ database, không tin giá do client gửi
            total += Decimal(product["price"]) * item["quantity"]
            lines.append((product["id"], item["quantity"], product["price"]))

        order = conn.execute(
            "INSERT INTO orders (user_id, total, shipping_address) VALUES (%s, %s, %s) RETURNING *",
            (user.id, total, shipping_address),
        ).fetchone()
        for product_id, quantity, unit_price in lines:
            conn.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price) "
                "VALUES (%s, %s, %s, %s)",
                (order["id"], product_id, quantity, unit_price),
            )
    return order


# Xem chi tiết đơn
@router.get("/orders/{order_id}")
def get_order(order_id: str, user: CurrentUser = Depends(authenticate)):
    with pool.connection() as conn:
        order = conn.execute("SELECT * FROM orders WHERE id = %s", (order_id,)).fetchone()
        if order is None:
            raise HttpError(404, "Không tìm thấy đơn hàng")

        # LỖI #1b: thiếu kiểm tra quyền sở hữu dữ liệu (tầng 2 của phân quyền).
        # Chỉ cần đăng nhập và đổi id trên đường dẫn là đọc được đơn của người khác.

        items = conn.execute(
            "SELECT product_id, quantity, unit_price FROM order_items WHERE order_id = %s ORDER BY id",
            (order["id"],),
        ).fetchall()
    return {**order, "items": items}


# Gửi nhận xét cho đơn hàng
@router.post("/orders/{order_id}/reviews", status_code=201)
def create_review(order_id: str, body: Any = Body(None), user: CurrentUser = Depends(authenticate)):
    # LỖI #1c: không kiểm tra đơn có thuộc về người gửi không; LỖI #9: không giới hạn độ dài.
    # LỖI #3 (XSS lưu trữ): nội dung được lưu nguyên văn, và frontend sẽ hiển thị bằng innerHTML.
    with pool.connection() as conn:
        return conn.execute(
            "INSERT INTO reviews (order_id, user_id, comment) VALUES (%s, %s, %s) RETURNING *",
            (order_id, user.id, body["comment"]),
        ).fetchone()


# Xem nhận xét của đơn hàng (LỖI #1c: cũng thiếu kiểm tra quyền sở hữu)
@router.get("/orders/{order_id}/reviews")
def list_reviews(order_id: str, user: CurrentUser = Depends(authenticate)):
    with pool.connection() as conn:
        return conn.execute(
            """SELECT r.id, r.comment, r.created_at, u.email
                 FROM reviews r JOIN users u ON u.id = r.user_id
                WHERE r.order_id = %s ORDER BY r.id""",
            (order_id,),
        ).fetchall()
