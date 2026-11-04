"""Thử cả ứng dụng qua HTTP nhưng không cần database: mọi kiểm tra ở đây xảy ra TRƯỚC khi chạm DB."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rate_limit import login_failures
from app.auth import sign_token
from app.routes.auth import LOGIN_ERROR

client = TestClient(app, raise_server_exceptions=False)


def bearer(role="customer", user_id=2):
    return {"Authorization": f"Bearer {sign_token(user_id, role)}"}


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"ok": True, "version": "secure"}


def test_security_headers_are_sent_on_every_response():
    for res in (client.get("/health"), client.get("/khong-co")):
        assert "script-src 'self'" in res.headers["content-security-policy"]
        assert "upgrade-insecure-requests" not in res.headers["content-security-policy"]
        assert res.headers["x-content-type-options"] == "nosniff"
        assert res.headers["x-frame-options"] == "SAMEORIGIN"


def test_cors_allows_listed_origin_only():
    ok = client.get("/health", headers={"Origin": "http://localhost:3002"})
    assert ok.headers["access-control-allow-origin"] == "http://localhost:3002"
    evil = client.get("/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in evil.headers


def test_unknown_path_returns_json_404():
    res = client.get("/khong-co")
    assert res.status_code == 404
    assert res.json() == {"error": "Không tìm thấy"}


def test_api_docs_are_not_exposed():
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_static_frontend_is_served():
    res = client.get("/")
    assert res.status_code == 200
    assert "BẢN ĐÃ SỬA" in res.text


@pytest.mark.parametrize(
    "method,path",
    [("GET", "/orders"), ("POST", "/orders"), ("GET", "/orders/1"), ("DELETE", "/products/1")],
)
def test_protected_endpoints_require_token(method, path):
    assert client.request(method, path).status_code == 401


def test_customer_cannot_delete_products():
    res = client.delete("/products/6", headers=bearer("customer"))
    assert res.status_code == 403
    assert res.json() == {"error": "Forbidden"}


@pytest.mark.parametrize("bad_id", ["abc", "1 OR 1=1", "0"])
def test_admin_gets_400_for_malformed_id(bad_id):
    res = client.delete(f"/products/{bad_id}", headers=bearer("admin", 1))
    assert res.status_code == 400
    assert res.json() == {"error": "id không hợp lệ"}


def test_invalid_order_rejected_before_touching_database():
    res = client.post("/orders", json={"items": [], "shippingAddress": "x"}, headers=bearer())
    assert res.status_code == 400
    assert res.json() == {"error": "Đơn hàng phải có từ 1 đến 20 sản phẩm"}


def test_malformed_json_is_400():
    res = client.post("/login", content="{bad", headers={"Content-Type": "application/json"})
    assert res.status_code == 400
    assert res.json() == {"error": "JSON không hợp lệ"}


def test_oversized_body_is_413():
    res = client.post("/login", json={"email": "a@shop.test", "password": "x" * 20_000})
    assert res.status_code == 413
    assert res.json() == {"error": "Dữ liệu quá lớn"}


def test_login_error_message_is_generic():
    res = client.post("/login", json={"email": "khong-phai-email", "password": "x"})
    assert res.status_code == 401
    assert res.json() == {"error": LOGIN_ERROR}


def test_login_is_blocked_with_429_after_too_many_failures():
    codes = [
        client.post("/login", json={"email": "khong-phai-email", "password": "x"}).status_code
        for _ in range(7)
    ]
    assert codes == [401] * 5 + [429] * 2
    res = client.post("/login", json={"email": "khong-phai-email", "password": "x"})
    assert int(res.headers["retry-after"]) > 0


def test_login_limiter_ignores_other_ips_state():
    for _ in range(5):
        login_failures.hit("203.0.113.9")
    assert client.post("/login", json={"email": "khong-phai-email", "password": "x"}).status_code == 401


def test_unexpected_error_is_hidden_from_caller():
    # Pool chưa mở nên truy vấn ném lỗi bất ngờ: người gọi chỉ thấy thông báo chung, không lộ chi tiết nội bộ
    res = client.get("/products")
    assert res.status_code == 500
    assert res.json() == {"error": "Lỗi máy chủ"}


def test_error_response_still_carries_cors_header():
    res = client.get("/products", headers={"Origin": "http://localhost:3002"})
    assert res.status_code == 500
    assert res.headers["access-control-allow-origin"] == "http://localhost:3002"
