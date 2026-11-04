#!/usr/bin/env bash
# Demo 4: CORS. Giả lập request từ một website lạ bằng header Origin.
# CORS do TRÌNH DUYỆT thực thi: curl vẫn nhận được dữ liệu, nhưng nhìn header trả về
# sẽ biết trình duyệt có cho trang lạ đọc phản hồi hay không.
source "$(dirname "$0")/lib.sh"

for BASE in "$VULN" "$SECURE"; do
  echo
  echo "################ $BASE ################"
  echo "--- Origin: http://evil.example ---"
  curl -s -D - -o /dev/null -H "Origin: http://evil.example" "$BASE/products" \
    | grep -i '^access-control' \
    || echo "(không có Access-Control-Allow-Origin -> trình duyệt sẽ CHẶN trang lạ đọc phản hồi)"
done
