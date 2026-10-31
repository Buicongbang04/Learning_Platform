---
title: Kết thúc TLS ở Nginx - chuyển hướng, HSTS, HTTP/2 và SNI lạ
level: intermediate
services: []
files:
  - path: starter/nginx.conf
    note: 3 TODO
  - path: tests/test_tls_termination.py
    note: Không sửa
  - path: tests/fixtures/backend.py
    note: Backend giả của Olist Shop
run:
  - docker pull nginx:1.30.6-alpine && docker pull python:3.12.16-alpine3.24
  - uv run pytest tracks/devops/modules/05-web-server-proxy/exercises/intermediate/02-tls-termination -q
---

## Mục tiêu

Dựng HTTPS cho `shop.olist.test` đúng như production cần: mọi thứ đi qua HTTPS trừ đường ACME, trình duyệt được dặn không
bao giờ dùng HTTP nữa, HTTP/2 bật, và Nginx không trả cert của bạn cho một tên miền lạ.

## Đề bài

Sửa `starter/nginx.conf` theo 3 TODO:

1. **Cổng 80** cho `shop.olist.test` chỉ làm hai việc:
   - `/.well-known/acme-challenge/<token>` trả tệp tĩnh từ thư mục `/var/www/acme` (tệp nằm ở
     `/var/www/acme/.well-known/acme-challenge/<token>`), không chuyển hướng. Đây là đường mà CA (Let's Encrypt) gọi để
     xác minh tên miền, bằng HTTP.
   - Mọi đường dẫn khác chuyển sang `https://shop.olist.test` giữ nguyên path và query, mã `301` hoặc `308`.
2. **Cổng 443** cho `shop.olist.test`: `ssl` và HTTP/2, cert `/etc/nginx/tls/fullchain.pem`, khoá
   `/etc/nginx/tls/privkey.pem`, chỉ `TLSv1.2` và `TLSv1.3`, proxy tới `olist_api` với `Host`, `X-Forwarded-For`,
   `X-Forwarded-Proto` đúng. Mọi response HTTPS, kể cả 404 và 5xx, có `Strict-Transport-Security` với `max-age` ít nhất
   `31536000` (một năm).
3. **Server mặc định cổng 443**: bắt tay TLS với SNI không phải `shop.olist.test`, hoặc không gửi SNI, bị từ chối (không
   trả cert nào).

**Môi trường test.** Test tự sinh một CA và cert cho `shop.olist.test` (SAN đúng tên, sống 30 ngày) bằng thư viện
`cryptography`, mount chỉ đọc vào `/etc/nginx/tls`; tạo tệp token ACME và mount vào `/var/www/acme`; chạy một backend giả,
`nginx -t`, rồi Nginx `1.30.6` mở cổng 80 và 443 trên `127.0.0.1` (cổng host ngẫu nhiên). Client HTTPS của test chỉ tin CA
vừa sinh và gửi SNI `shop.olist.test`. Không có kết nối nào ra Internet. Test kiểm:

1. HTTP `GET /orders/abc?utm_source=email&x=1` và HTTP `POST /jobs/recompute`: `301` hoặc `308`, `Location` đúng bằng
   `https://shop.olist.test` + path và query gốc.
2. HTTP `GET /.well-known/acme-challenge/Xk2-olist-acme-token`: 200, nội dung đúng tệp.
3. HTTPS `GET /orders/abc?x=1`: 200, backend nhận `X-Forwarded-Proto: https`, `Host: shop.olist.test`, đúng path.
4. HTTPS `GET /healthz` (200) và `GET /khong-co` (404 từ backend): cả hai có HSTS `max-age >= 31536000`.
5. Bắt tay mời ALPN `h2, http/1.1` với SNI `shop.olist.test`: server chọn `h2`.
6. Bắt tay với SNI `shop.olist.test` thành công; với SNI `evil.example` và không có SNI thì thất bại.
7. Chạy starter ban đầu (`tests/fixtures/nginx.starter.conf`): mọi phép kiểm trên phải bắt được lỗi.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/05-web-server-proxy/exercises/intermediate/02-tls-termination -q` pass.
- Giải thích vì sao `301` có thể làm hỏng `POST` từ client cũ còn `308` thì không, và vì sao nên phục vụ đường ACME thẳng
  trên HTTP thay vì để nó đi theo redirect sang khối HTTPS.
- Nói được rủi ro của HSTS `includeSubDomains` và `preload` với một tên miền còn subdomain chưa có HTTPS, và cách rút lại.
- Nói được vì sao `ssl_reject_handshake` tốt hơn một server mặc định trả cert tự ký.

## Gợi ý

### Gợi ý 1

`return 301 https://$host$request_uri;` giữ path và query. `location ^~ /.well-known/acme-challenge/ { root /var/www/acme; }`
khớp trước các location regex. Từ Nginx 1.25.1, HTTP/2 bật bằng chỉ thị riêng `http2 on;`, không còn là tham số của
`listen`.

### Gợi ý 2

`add_header` không có tham số `always` chỉ áp cho mã 200, 201, 204, 206, 301, 302, 303, 304, 307, 308. Thêm một
`add_header` bất kỳ trong `location` làm mọi `add_header` ở mức `server` không còn được kế thừa vào location đó.
`ssl_reject_handshake on;` đặt trong khối `listen 443 ssl default_server;`.
