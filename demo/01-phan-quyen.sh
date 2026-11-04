#!/usr/bin/env bash
# Demo 1: phân quyền (tầng 1: vai trò, tầng 2: quyền sở hữu dữ liệu)
# Lưu ý: bản vulnerable sẽ XÓA sản phẩm #6. Chạy lại seed để khôi phục:
#   docker compose run --rm seed
source "$(dirname "$0")/lib.sh"

for BASE in "$VULN" "$SECURE"; do
  echo
  echo "################ $BASE ################"
  TOKEN_A=$(login "$BASE" a@shop.test 'CustomerA@123') || exit 1

  echo
  echo "--- Khách A xem đơn #1 (đơn của chính A) -> mong đợi 200 ---"
  req "$BASE/orders/1" -H "Authorization: Bearer $TOKEN_A"

  echo
  echo "--- Khách A đổi id sang #3 (đơn của khách B) -> bản đúng phải trả 403 ---"
  req "$BASE/orders/3" -H "Authorization: Bearer $TOKEN_A"

  echo
  echo "--- Khách A xóa sản phẩm #6 (chỉ admin được phép) -> bản đúng phải trả 403 ---"
  req -X DELETE "$BASE/products/6" -H "Authorization: Bearer $TOKEN_A"
done
