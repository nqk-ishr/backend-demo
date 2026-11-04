#!/usr/bin/env bash
# Hàm dùng chung cho các script demo. Cần: bash, curl.
VULN="${VULN:-http://localhost:3001}"
SECURE="${SECURE:-http://localhost:3002}"

# Gọi API và in kèm mã HTTP
req() {
  curl -s -w '\n=> HTTP %{http_code}\n' "$@"
}

# login <base-url> <email> <mật khẩu>  -> in ra token
login() {
  local body
  body=$(curl -s -X POST "$1/login" -H 'Content-Type: application/json' \
    -d "{\"email\":\"$2\",\"password\":\"$3\"}")
  if [[ "$body" == *'"token"'* ]]; then
    echo "$body" | sed -E 's/.*"token":"([^"]+)".*/\1/'
  else
    echo "Đăng nhập thất bại ($1): $body" >&2
    return 1
  fi
}
