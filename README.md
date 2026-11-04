# Demo bảo mật và triển khai Backend: dịch vụ bán hàng

Repo demo cho phần **"Triển khai và bảo mật trong Backend"**. Cùng một dịch vụ bán hàng (người dùng, sản phẩm, đơn hàng, nhận xét) được viết thành **hai phiên bản**:

| Phiên bản | Địa chỉ | Mục đích |
| --- | --- | --- |
| `vulnerable/` | http://localhost:3001 | Có lỗi **cố ý** (đánh dấu `LỖI #n` trong code). **Chỉ chạy trên máy local, không deploy.** |
| `secure/` | http://localhost:3002 | Bản đã sửa (đánh dấu `SỬA #n` trong code) |

Cả hai dùng **chung một database PostgreSQL** và cùng dữ liệu mẫu, nên một request gửi vào hai cổng cho hai kết quả khác nhau. Mỗi khối demo theo mẫu: **tấn công bản lỗi → thấy hậu quả → chạy lại trên bản sửa → nói tên cơ chế đã chặn**.

> **Backend viết bằng FastAPI (Python 3.12).** Đã chuyển từ bản Node.js/Express ban đầu, giữ nguyên hành vi API, mã lỗi và các điểm `LỖI #n` / `SỬA #n`.
>
> **Trạng thái kiểm chứng:** đã chạy 60 test của bản `secure` (không cần database) và chạy cả hai bản API với PostgreSQL 16 thật cùng schema, `02-roles.sh` và `seed.py`; các script `demo/01` đến `demo/04` cho đúng kết quả trong phần "Kịch bản demo". **Chưa kiểm tra:** `docker compose up` và `docker build` (môi trường kiểm tra không có Docker daemon dùng được), khối demo XSS trên trình duyệt, và workflow GitHub Actions. Lần chạy Docker đầu có thể lộ lỗi nhỏ, nhóm hãy sửa và ghi lại.

## Cấu trúc repo

```
order-security-demo/
├── docker-compose.yml        # db + vulnerable + secure (+ seed)
├── .env.example              # mẫu cấu hình; .env thật KHÔNG commit
├── db/
│   ├── init/01-schema.sql    # 5 bảng
│   ├── init/02-roles.sh      # tài khoản app_user quyền tối thiểu
│   └── seed.py               # dữ liệu mẫu (băm mật khẩu bằng bcrypt)
├── vulnerable/               # bản có lỗi
├── secure/                   # bản đã sửa + test
├── demo/                     # script curl cho từng khối demo
└── .github/workflows/ci.yml  # test, kiểm tra secret, build image
```

## Chạy nhanh

Cần: Docker Desktop (hoặc Docker Engine + Compose v2).

```bash
cp .env.example .env
# Mở .env và điền DB_PASSWORD, APP_DB_PASSWORD (chữ và số), JWT_SECRET (>= 32 ký tự):
#   python -c "import secrets; print(secrets.token_hex(32))"

docker compose up -d --build
docker compose run --rm seed        # nạp dữ liệu mẫu
```

Mở http://localhost:3001 (bản lỗi) và http://localhost:3002 (bản sửa).

**Đặt lại về trạng thái ban đầu trước mỗi buổi demo:** `docker compose run --rm seed`.
**Xóa sạch kể cả schema:** `docker compose down -v` rồi chạy lại các lệnh trên. Nhớ cờ `-v`: script trong `db/init` chỉ chạy khi volume còn trống.

### Tài khoản mẫu (chỉ dùng cho demo)

| Vai trò | Email | Mật khẩu | id |
| --- | --- | --- | --- |
| admin | admin@shop.test | Admin@12345 | 1 |
| khách A | a@shop.test | CustomerA@123 | 2 |
| khách B | b@shop.test | CustomerB@123 | 3 |

Đơn #1, #2 là của khách A; đơn #3 là của khách B. Sản phẩm #6 chưa có trong đơn nào nên xóa được.

## API

| Method và đường dẫn | Quyền | Ghi chú |
| --- | --- | --- |
| `POST /register` | công khai | body: `email`, `password` |
| `POST /login` | công khai | trả `token` (JWT) |
| `GET /products?search=` | công khai | tìm theo tên |
| `DELETE /products/:id` | **admin** | |
| `GET /orders` | đăng nhập | khách thấy đơn của mình, admin thấy tất cả |
| `POST /orders` | đăng nhập | body: `items: [{productId, quantity}]`, `shippingAddress`; chạy trong một giao dịch |
| `GET /orders/:id` | **chủ đơn hoặc admin** | |
| `POST /orders/:id/reviews`, `GET /orders/:id/reviews` | **chủ đơn hoặc admin** | body: `comment` |

Gửi token trong header `Authorization: Bearer <token>`.

## Bảng đối chiếu: lỗi, cách sửa, file, phần lý thuyết

| # | Chủ đề | Bản có lỗi | Bản đã sửa | File | Lý thuyết |
| --- | --- | --- | --- | --- | --- |
| 1a | Phân quyền tầng 1 | Xóa sản phẩm chỉ cần đăng nhập | `Depends(require_role('admin'))` | `routes/products.py`, `auth.py` | Phần 1 |
| 1b | Phân quyền tầng 2 | Đổi id là đọc được đơn của người khác | `load_order_for_user` đối chiếu chủ đơn, trả 403 | `routes/orders.py` | Phần 1 |
| 2 | SQL Injection | Nối chuỗi vào câu SQL | Prepared statement (`%s`) | `routes/products.py` | Phần 3 |
| 3 | XSS | `innerHTML`, không có CSP | `textContent` + header CSP (`middleware.py`) | `public/app.js`, `middleware.py` | Phần 3 |
| 4 | JWT và đăng nhập | Secret yếu viết cứng, token không hết hạn, lộ email đã đăng ký | Secret từ môi trường (>= 32 ký tự), hạn 15 phút, thông báo chung | `auth.py`, `config.py`, `routes/auth.py` | Phần 1, 4 |
| 5 | Rate limiting | Không giới hạn | 5 lần đăng nhập sai / 15 phút, trả 429 | `rate_limit.py` | Phần 2 |
| 6 | CORS | Cho mọi origin | Danh sách origin tin cậy | `main.py` | Phần 2 |
| 7 | Lộ lỗi nội bộ | Trả nguyên lỗi SQL | Thông báo chung, chi tiết ghi vào log | `errors.py`, `middleware.py` | Phần 3 |
| 8 | Quyền database | Kết nối bằng superuser | `app_user` chỉ có quyền cần thiết | `docker-compose.yml`, `db/init/02-roles.sh` | Phần 3, 4 |
| 9 | Kiểm tra đầu vào | Tin mọi dữ liệu gửi lên | Kiểm tra kiểu, độ dài, miền giá trị | `validate.py` | Phần 3 |

Ngoài ra cả hai bản đều: băm mật khẩu bằng bcrypt (cost 12), khóa dòng khi đặt hàng (`FOR UPDATE`), lấy giá từ database chứ không tin client.

## Kịch bản demo

Các script cần `bash` và `curl` (Git Bash hoặc WSL trên Windows). Mỗi script chạy lần lượt trên bản lỗi rồi bản sửa.

### Khối 1: Phân quyền (~50 giây)
```bash
./demo/01-phan-quyen.sh
```
Khách A đọc được đơn #3 của khách B và xóa được sản phẩm trên bản lỗi (200 và 204); bản sửa trả **403** cả hai. Nói: tầng 1 kiểm tra vai trò ở middleware, tầng 2 kiểm tra chủ dữ liệu trong handler, thiếu tầng nào cũng hở. Bản lỗi sẽ xóa sản phẩm #6; chạy `docker compose run --rm seed` để khôi phục.

### Khối 2: SQL Injection (~50 giây)
```bash
./demo/02-sql-injection.sh
```
Bản lỗi: payload `' OR 1=1 --` trả cả bảng, payload UNION lộ email và chuỗi băm mật khẩu, một dấu nháy làm lộ lỗi SQL. Bản sửa: các payload chỉ là chuỗi tìm kiếm, trả mảng rỗng. Nói: dữ liệu và câu lệnh đi riêng nên dữ liệu không thành lệnh. Mở `secure/app/routes/products.py` đặt cạnh `vulnerable/app/routes/products.py`.

### Khối 3: XSS (~50 giây, làm trên trình duyệt)
1. Mở http://localhost:3001, đăng nhập (mặc định là khách A), mục 3 để id = 1.
2. Ở mục 4 nhập nhận xét: `<img src=x onerror="alert(localStorage.getItem('token'))">` rồi bấm **Gửi nhận xét**, sau đó **Tải nhận xét**.
3. Bản lỗi hiện hộp thoại chứa token: mã chạy trên trình duyệt người xem, đọc được `localStorage`.
4. Lặp lại trên http://localhost:3002: nhận xét hiện thành **chữ**, không chạy. Mở DevTools, tab Network, xem header `Content-Security-Policy` ở bản sửa.

Payload chỉ hiện token cho chính người đang xem, không gửi đi đâu.

### Khối 4: Rate limiting (~30 giây)
```bash
./demo/03-rate-limit.sh
```
Bản lỗi luôn trả 401; bản sửa trả 401 năm lần rồi **429**. Chạy lại ngay: `docker compose restart secure`.

### Khối 5: Docker, CI/CD, secret (~40 giây)
- `docker compose ps`: nhiều container chạy cùng lúc từ một lệnh.
- Mở `.gitignore` và `.env.example`: `.env` không bao giờ lên Git.
- Làm app từ chối chạy khi thiếu secret: `docker compose run --rm -e JWT_SECRET=ngan secure` báo lỗi `JWT_SECRET phải dài ít nhất 32 ký tự`.
- Trên GitHub tab Actions: một lần xanh, và một lần đỏ (cố tình sửa một test) cho thấy bước build/deploy không chạy.
- Cho xem `docker compose exec db psql -U postgres -d shop -c "SELECT email, password_hash FROM users"`: chỉ có chuỗi bcrypt.

### Phụ: CORS (nếu còn thời gian)
```bash
./demo/04-cors.sh
```
Bản lỗi trả `Access-Control-Allow-Origin: *`, bản sửa không trả header này cho origin lạ. CORS do **trình duyệt** thực thi, curl vẫn nhận dữ liệu; vì vậy CORS không thay được xác thực và phân quyền.

## Thứ tự làm và chia việc cho 4 người

Thứ tự phụ thuộc: **hợp đồng chung → CSDL và Docker Compose → API (bản lỗi) → gia cố (bản sửa) → test, CI/CD, tập demo**.

| Vai | Phụ trách | File chính |
| --- | --- | --- |
| A. API và giao tiếp | Endpoint, mã trạng thái, validate, CORS, frontend tối giản | `routes/*.py`, `validate.py`, `public/` |
| B. Cơ sở dữ liệu | Schema, seed, giao dịch đặt hàng, truy vấn, quyền `app_user` | `db/`, `routes/orders.py` |
| C. Bảo mật ứng dụng | bcrypt, JWT, phân quyền hai tầng, rate limiting, CSP | `auth.py`, `rate_limit.py`, `main.py` |
| D. Triển khai | Dockerfile, Compose, `.env`, CI/CD, script demo | `docker-compose.yml`, `.github/`, `demo/` |

Mỗi người nên tự chạy **cả năm khối demo** và hỏi chéo nhau bằng câu hỏi ở cuối mỗi phần lý thuyết.

## Chạy test

```bash
cd secure
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest
```
Test không cần database. Các thư viện trong `requirements.txt` đã ghim đúng phiên bản (`==`), nên không cần file khóa riêng.

## Ghi chú khi chuyển từ Express sang FastAPI

| Express (bản cũ) | FastAPI (bản này) |
| --- | --- |
| `authenticate`, `requireRole('admin')` là middleware gắn theo route | Là **dependency**: `Depends(authenticate)`, `Depends(require_role('admin'))`. Middleware thật của FastAPI (ASGI) dùng cho việc áp dụng toàn cục như CORS, header bảo mật, giới hạn body |
| `req.user` | Giá trị trả về của dependency `authenticate`, handler nhận qua tham số `user: CurrentUser` |
| `helmet`, `cors`, `express-rate-limit` | `middleware.py` (header bảo mật), `CORSMiddleware`, `rate_limit.py` (tự viết, bộ đếm trong bộ nhớ) |
| `pg`, `bcryptjs`, `jsonwebtoken` | `psycopg` (pool), `bcrypt`, `PyJWT` |
| Tiền tính bằng `Number` | Tính bằng `Decimal`; cột NUMERIC trả về JSON dạng chuỗi `"150000.00"` |
| `sub` trong JWT là số | `sub` là chuỗi (đúng chuẩn JWT, PyJWT yêu cầu vậy). Riêng bản `vulnerable` vẫn chấp nhận `sub` là số để demo token giả |
| `/docs` không có | FastAPI tự sinh `/docs`: bật ở `vulnerable` (tiện thử tay), tắt ở `secure` |

## Giới hạn đã biết, nhóm có thể mở rộng

- **Token lưu trong `localStorage`** nên XSS vẫn đọc được nếu escape và CSP đều bị vượt. Hướng nâng cấp: cookie `HttpOnly` + `Secure` + `SameSite` (khi đó cần thêm biện pháp chống CSRF).
- **Chưa có refresh token**, token hết hạn thì phải đăng nhập lại.
- **Rate limiting dùng bộ nhớ trong**; chạy nhiều server hoặc nhiều worker uvicorn thì cần Redis. Sau reverse proxy phải cho uvicorn tin `X-Forwarded-For` (`--forwarded-allow-ips`).
- **Chưa có HTTPS** trong Compose. Có thể thêm Caddy hoặc Nginx làm reverse proxy rồi bật HSTS.
- **Role nằm trong JWT** có thể cũ khi quyền vừa đổi; thao tác nhạy cảm nên tra lại database.
- Thêm quét secret (ví dụ gitleaks) vào CI.

## Xử lý sự cố thường gặp

- **`Thiếu DB_PASSWORD trong .env`**: chưa tạo file `.env` từ `.env.example`.
- **App báo lỗi kết nối hoặc thiếu bảng**: volume cũ còn từ lần chạy trước, chạy `docker compose down -v` rồi `up` lại.
- **Cổng 3001/3002/5432 đã bị chiếm**: đổi cổng bên trái trong `docker-compose.yml`.
- **`02-roles.sh` lỗi trên Windows**: file phải dùng kết thúc dòng LF; `.gitattributes` đã ép LF, nếu vẫn lỗi hãy clone lại repo.
- **Script demo báo "Đăng nhập thất bại"**: chưa chạy seed, hoặc bản `secure` vừa bị rate limit (restart container).
