"""SỬA #9: kiểm tra đầu vào ở server.

Kiểm tra ở frontend không thay thế được vì kẻ tấn công có thể gọi API trực tiếp bằng curl hoặc Postman.
"""
import re
from typing import Any

from .errors import HttpError

# fullmatch (không dùng "$") để chuỗi có xuống dòng ở cuối không lọt qua
_EMAIL_RE = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
# Chỉ chữ số ASCII: \d của Python còn khớp cả chữ số của các hệ chữ khác
_ID_RE = re.compile(r"[0-9]{1,9}")
_MAX_INT4 = 2_147_483_647


def _is_int(value: Any) -> bool:
    # bool là lớp con của int trong Python; true/false không được coi là số
    return isinstance(value, int) and not isinstance(value, bool)


def is_email(value: Any) -> bool:
    return isinstance(value, str) and len(value) <= 254 and _EMAIL_RE.fullmatch(value) is not None


def is_password(value: Any) -> bool:
    # bcrypt chỉ xét tối đa 72 byte đầu của mật khẩu
    return isinstance(value, str) and len(value) >= 8 and len(value.encode("utf-8")) <= 72


def parse_id(value: Any) -> int:
    if not isinstance(value, str) or _ID_RE.fullmatch(value) is None or int(value) < 1:
        raise HttpError(400, "id không hợp lệ")
    return int(value)


def validate_search(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str) or len(value) > 100:
        raise HttpError(400, "Từ khóa tìm kiếm không hợp lệ")
    return value


def validate_order_input(body: Any) -> dict:
    if not isinstance(body, dict):
        raise HttpError(400, "Dữ liệu gửi lên không hợp lệ")
    items = body.get("items")
    shipping_address = body.get("shippingAddress")

    if not isinstance(items, list) or not 1 <= len(items) <= 20:
        raise HttpError(400, "Đơn hàng phải có từ 1 đến 20 sản phẩm")

    seen: set[int] = set()
    clean_items = []
    for item in items:
        if not isinstance(item, dict):
            raise HttpError(400, "Sản phẩm trong đơn không hợp lệ")
        product_id, quantity = item.get("productId"), item.get("quantity")
        if not _is_int(product_id) or not 1 <= product_id <= _MAX_INT4:
            raise HttpError(400, "productId không hợp lệ")
        if not _is_int(quantity) or not 1 <= quantity <= 100:
            raise HttpError(400, "quantity phải là số nguyên từ 1 đến 100")
        if product_id in seen:
            raise HttpError(400, "Sản phẩm bị lặp trong đơn")
        seen.add(product_id)
        clean_items.append({"productId": product_id, "quantity": quantity})

    if not isinstance(shipping_address, str):
        raise HttpError(400, "Thiếu địa chỉ giao hàng")
    address = shipping_address.strip()
    if not 5 <= len(address) <= 200:
        raise HttpError(400, "Địa chỉ giao hàng phải từ 5 đến 200 ký tự")

    return {"items": clean_items, "shippingAddress": address}


def validate_comment(body: Any) -> str:
    comment = body.get("comment") if isinstance(body, dict) else None
    if not isinstance(comment, str):
        raise HttpError(400, "Thiếu nội dung nhận xét")
    trimmed = comment.strip()
    if not 1 <= len(trimmed) <= 500:
        raise HttpError(400, "Nhận xét phải từ 1 đến 500 ký tự")
    return trimmed
