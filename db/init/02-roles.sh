#!/bin/bash
# Tạo tài khoản database quyền tối thiểu cho bản "secure" (nguyên tắc quyền tối thiểu).
# Bản "vulnerable" dùng superuser postgres nên nếu bị SQL Injection thì thiệt hại lớn hơn nhiều.
set -e

psql -v ON_ERROR_STOP=1 -v app_pw="$APP_DB_PASSWORD" \
     --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'EOSQL'
CREATE ROLE app_user LOGIN PASSWORD :'app_pw';

GRANT USAGE ON SCHEMA public TO app_user;

-- Chỉ cấp đúng thao tác ứng dụng cần, không cấp DROP/ALTER/TRUNCATE
GRANT SELECT, INSERT ON users, orders, order_items, reviews TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON products TO app_user;   -- UPDATE: trừ tồn kho, DELETE: admin xóa sản phẩm
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
EOSQL
