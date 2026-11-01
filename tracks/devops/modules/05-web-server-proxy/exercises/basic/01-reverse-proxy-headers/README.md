---
title: Reverse proxy cho Olist Shop - header, IP client và request id
level: basic
services: []
files:
  - path: starter/nginx.conf
    note: 5 TODO
  - path: tests/test_reverse_proxy.py
    note: Không sửa
  - path: tests/fixtures/backend.py
    note: Backend giả của Olist Shop, đọc để biết nó trả gì
run:
  - docker pull nginx:1.30.6-alpine && docker pull python:3.12.16-alpine3.24
  - uv run pytest tracks/devops/modules/05-web-server-proxy/exercises/basic/01-reverse-proxy-headers -q
---

## Mục tiêu

Đặt Nginx trước API của Olist Shop sao cho API vẫn biết request thật đến từ đâu (tên miền, IP client, HTTP hay HTTPS),
mỗi request có một id lần theo được qua cả Nginx lẫn API, và client không giả được những thông tin đó.

## Đề bài

Nginx là tầng ngoài cùng (không có load balancer hay CDN phía trước), nghe cổng 80 cho `shop.olist.test`, chuyển request
tới upstream `olist_api` (một backend `olist-api-1:8000`). Sửa `starter/nginx.conf` theo 5 TODO:

| Yêu cầu | Chi tiết |
| --- | --- |
| Path và query | Backend nhận nguyên path và query client gửi (`/orders/abc123?expand=items`) |
| `Host` | Backend nhận `Host: shop.olist.test`, không phải tên upstream |
| `X-Forwarded-Proto` | Giao thức client dùng với Nginx (`http` ở bài này) |
| `X-Real-IP`, `X-Forwarded-For` | Cả hai là đúng IP client mà Nginx thấy. Client tự gửi hai header này thì giá trị đó bị bỏ, không được nối thêm |
| `X-Request-ID` | Client gửi id hợp lệ (1–64 ký tự, chỉ gồm chữ, số, `.`, `_`, `-`) thì giữ nguyên; không gửi hoặc gửi sai dạng thì Nginx sinh id mới bằng `$request_id` (32 ký tự hex) |
| Access log | Mỗi dòng log ghi đúng id mà backend nhận |
| Host lạ | Request có `Host` khác `shop.olist.test` không được tới backend: trả `421` hoặc đóng kết nối (`return 444`) |
| Header `Server` | Đúng `nginx`, không lộ phiên bản |

**Môi trường test.** Test tạo một docker network riêng, chạy backend giả `tests/fixtures/backend.py` (cùng route với API
Olist Shop; mỗi response JSON trả lại path, `Host`, `X-Forwarded-*`, `X-Real-IP`, `X-Request-ID` mà nó nhận, và đặt header
`X-Request-ID` của response bằng id nó nhận), rồi chạy `nginx -t` và Nginx `1.30.6` với **bản sao** cấu hình của bạn mount
chỉ đọc vào `/etc/nginx/nginx.conf`. Cổng chỉ mở trên `127.0.0.1`, container tự xoá khi xong. Thiếu Docker hoặc chưa pull
image thì test skip kèm lệnh cần chạy. Muốn thử tay, dùng lab ở mục 0 của lý thuyết.

Test kiểm:

1. `GET /orders/abc123?expand=items` với `Host: shop.olist.test`: 200, backend nhận đúng path, `Host`, `X-Forwarded-Proto: http`.
2. Gửi kèm `X-Forwarded-For: 6.6.6.6` và `X-Real-IP: 6.6.6.6`: backend nhận hai header bằng nhau, là một địa chỉ IP, không
   chứa `6.6.6.6`.
3. Gửi `X-Request-ID: checkout-<8 hex>.retry_1`: backend nhận nguyên id, response có đúng một header `X-Request-ID` bằng id
   đó, access log của Nginx chứa id đó. Không gửi, gửi `abc def`, gửi chuỗi 65 ký tự: backend nhận id 32 ký tự hex,
   response trả lại đúng id đó, access log chứa id đó.
4. `Host: evil.example`: nhận `421` hoặc kết nối bị đóng không có response.
5. Header `Server` của response là `nginx`.
6. Một test nữa chạy chính starter ban đầu (`tests/fixtures/nginx.starter.conf`) và đòi các phép kiểm trên bắt được lỗi
   của nó: test không pass nhờ một cấu hình làm sai.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/05-web-server-proxy/exercises/basic/01-reverse-proxy-headers -q` pass.
- Giải thích được vì sao ở tầng ngoài cùng không dùng `$proxy_add_x_forwarded_for`, và khi nào thì lại phải dùng nó.
- Chỉ ra được trong log của Nginx và của API cùng một request id cho một request bạn tự gửi bằng `curl`.

## Gợi ý

### Gợi ý 1

`proxy_pass` không tự đặt `Host` theo request: mặc định nó gửi `$proxy_host` (tên upstream). Biến cần dùng: `$host`,
`$remote_addr`, `$scheme`. Header nào client gửi mà bạn không `proxy_set_header` thì Nginx chuyển nguyên cho backend.

### Gợi ý 2

`map` đặt ở mức `http`, so khớp regex khi giá trị bắt đầu bằng `~` (đặt cả chuỗi trong ngoặc kép vì có `{`). Server mặc
định là khối có `listen 80 default_server;`, `server_name _;`. `server_tokens off;` ẩn phiên bản.
