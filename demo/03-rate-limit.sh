#!/usr/bin/env bash
# Demo 3: rate limiting ở /login. Bản secure cho 5 lần sai, từ lần 6 trả 429.
# Muốn chạy lại ngay: docker compose restart secure   (bộ đếm nằm trong bộ nhớ)
source "$(dirname "$0")/lib.sh"

for BASE in "$VULN" "$SECURE"; do
  echo
  echo "################ $BASE ################"
  for i in 1 2 3 4 5 6 7; do
    code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/login" \
      -H 'Content-Type: application/json' \
      -d '{"email":"a@shop.test","password":"mat-khau-sai"}')
    echo "Lần thử $i -> HTTP $code"
  done
done
