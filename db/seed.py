"""Nạp dữ liệu mẫu cố định. Chạy lại bao nhiêu lần cũng được: script xóa sạch rồi nạp lại.

Chạy: docker compose run --rm seed
"""
import os
import sys

import bcrypt
import psycopg

# Mật khẩu dưới đây CHỈ DÙNG CHO DEMO.
USERS = [
    ("admin@shop.test", "Admin@12345", "admin"),       # id 1
    ("a@shop.test", "CustomerA@123", "customer"),      # id 2
    ("b@shop.test", "CustomerB@123", "customer"),      # id 3
]

# (tên, mô tả, giá, tồn kho) -> id 1..6
PRODUCTS = [
    ("Áo thun cotton", "Áo thun cotton 100%, nhiều màu", 150000, 50),
    ("Quần jean nam", "Quần jean ống đứng", 450000, 30),
    ("Giày sneaker", "Giày thể thao đế êm", 890000, 20),
    ("Balo laptop", "Balo chống nước, ngăn laptop 15 inch", 520000, 15),
    ("Mũ lưỡi trai", "Mũ lưỡi trai thêu logo", 90000, 100),
    ("Tai nghe Bluetooth", "Pin 20 giờ, chống ồn nhẹ", 650000, 25),  # chưa có trong đơn nào -> xóa được khi demo
]

# Đơn của khách A (user 2) là #1, #2; đơn của khách B (user 3) là #3.
# items: (productId, quantity)
ORDERS = [
    {"user": 2, "status": "paid", "address": "12 Lê Lợi, Hà Nội", "items": [(1, 2), (5, 1)]},
    {"user": 2, "status": "pending", "address": "12 Lê Lợi, Hà Nội", "items": [(3, 1)]},
    {"user": 3, "status": "paid", "address": "45 Trần Hưng Đạo, Đà Nẵng", "items": [(2, 1), (4, 1)]},
]

# (chỉ số đơn (từ 0), userId, nhận xét)
REVIEWS = [
    (0, 2, "Giao hàng nhanh, đóng gói cẩn thận."),
    (2, 3, "Quần đẹp, đúng size."),
]


def main() -> None:
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.transaction():
        conn.execute("TRUNCATE reviews, order_items, orders, products, users RESTART IDENTITY CASCADE")

        for email, password, role in USERS:
            hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(12)).decode("ascii")
            conn.execute(
                "INSERT INTO users (email, password_hash, role) VALUES (%s, %s, %s)",
                (email, hashed, role),
            )

        for name, description, price, stock in PRODUCTS:
            conn.execute(
                "INSERT INTO products (name, description, price, stock) VALUES (%s, %s, %s, %s)",
                (name, description, price, stock),
            )

        order_ids = []
        for order in ORDERS:
            total = sum(PRODUCTS[pid - 1][2] * qty for pid, qty in order["items"])
            order_id = conn.execute(
                "INSERT INTO orders (user_id, status, total, shipping_address) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (order["user"], order["status"], total, order["address"]),
            ).fetchone()[0]
            order_ids.append(order_id)
            for pid, qty in order["items"]:
                conn.execute(
                    "INSERT INTO order_items (order_id, product_id, quantity, unit_price) "
                    "VALUES (%s, %s, %s, %s)",
                    (order_id, pid, qty, PRODUCTS[pid - 1][2]),
                )

        for order_index, user_id, comment in REVIEWS:
            conn.execute(
                "INSERT INTO reviews (order_id, user_id, comment) VALUES (%s, %s, %s)",
                (order_ids[order_index], user_id, comment),
            )

    print("Đã nạp dữ liệu mẫu:")
    for email, password, role in USERS:
        print(f"  {role.ljust(8)} {email}  /  {password}")
    print(f"  {len(PRODUCTS)} sản phẩm, {len(ORDERS)} đơn hàng, {len(REVIEWS)} nhận xét")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Nạp dữ liệu thất bại: {exc}", file=sys.stderr)
        sys.exit(1)
