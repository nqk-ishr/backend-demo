import pytest

from app.errors import HttpError
from app.validate import (
    is_email,
    is_password,
    parse_id,
    validate_comment,
    validate_order_input,
    validate_search,
)

ADDR = "12 Lê Lợi, Hà Nội"


def status_of(fn, *args):
    with pytest.raises(HttpError) as info:
        fn(*args)
    return info.value.status


def test_email_valid_and_invalid():
    assert is_email("a@shop.test") is True
    assert is_email("khong-phai-email") is False
    assert is_email(123) is False
    assert is_email("a@shop.test\n") is False  # xuống dòng ở cuối không lọt qua


def test_password_min_8_chars_max_72_bytes():
    assert is_password("Abcdefg1") is True
    assert is_password("ngan") is False
    assert is_password("x" * 73) is False
    assert is_password("é" * 40) is False  # 40 ký tự nhưng 80 byte


def test_parse_id_accepts_only_positive_integers():
    assert parse_id("42") == 42
    for bad in ["abc", "1 OR 1=1", "0", None, "١٢٣", "-1", "1234567890"]:
        assert status_of(parse_id, bad) == 400


def test_search_limits_length_and_type():
    assert validate_search(None) == ""
    assert validate_search("áo") == "áo"
    assert status_of(validate_search, "x" * 101) == 400
    assert status_of(validate_search, ["a", "b"]) == 400


def test_valid_order_is_accepted_and_address_trimmed():
    result = validate_order_input(
        {"items": [{"productId": 1, "quantity": 2}], "shippingAddress": f"  {ADDR}  "}
    )
    assert result["items"] == [{"productId": 1, "quantity": 2}]
    assert result["shippingAddress"] == ADDR


@pytest.mark.parametrize(
    "body",
    [
        None,
        {"items": [], "shippingAddress": ADDR},
        {"items": [{"productId": 1, "quantity": -5}], "shippingAddress": ADDR},
        {"items": [{"productId": 1, "quantity": 1.5}], "shippingAddress": ADDR},
        {"items": [{"productId": 1, "quantity": True}], "shippingAddress": ADDR},
        {"items": [{"productId": "1", "quantity": 1}], "shippingAddress": ADDR},
        {"items": [{"productId": 1, "quantity": 1}, {"productId": 1, "quantity": 2}], "shippingAddress": ADDR},
        {"items": [{"productId": 1, "quantity": 1}], "shippingAddress": "ab"},
        {"items": [{"productId": 1, "quantity": 1}]},
        {"items": [{"productId": 1, "quantity": 1}] * 21, "shippingAddress": ADDR},
    ],
)
def test_invalid_orders_are_rejected(body):
    assert status_of(validate_order_input, body) == 400


def test_comment_not_empty_max_500_chars():
    assert validate_comment({"comment": "  tốt  "}) == "tốt"
    for bad in [{"comment": "   "}, {"comment": "x" * 501}, {}, None]:
        assert status_of(validate_comment, bad) == 400
