---
title: Load balancing hai bản API và passive health check
level: basic
services: []
files:
  - path: starter/nginx.conf
    note: 2 TODO
  - path: tests/test_load_balancing.py
    note: Không sửa
  - path: tests/fixtures/backend.py
    note: Backend giả của Olist Shop
run:
  - docker pull nginx:1.30.6-alpine && docker pull python:3.12.16-alpine3.24
  - uv run pytest tracks/devops/modules/05-web-server-proxy/exercises/basic/02-upstream-load-balancing -q
---

## Mục tiêu

Chia tải cho hai bản API có sức mạnh khác nhau, và khi một bản chết thì người dùng không thấy lỗi còn Nginx thôi gửi
request vào bản đó. Bạn sẽ thấy tận mắt passive health check làm được gì và không làm được gì.

## Đề bài

Olist Shop chạy hai bản API: `olist-api-1:8000` trên máy cũ và `olist-api-2:8000` trên máy mới mạnh gấp ba. Sửa
`starter/nginx.conf`:

1. Upstream `olist_api` có cả hai server, `olist-api-2` có `weight=3`.
2. Cả hai server có `max_fails=3 fail_timeout=30s`.

Giữ nguyên `log_format upstreamlog` và `worker_processes 1` của starter: test đọc `up=$upstream_addr` trong access log để
biết Nginx đã thử backend nào. Một worker làm thứ tự chọn backend xác định được; mục 3 của lý thuyết nói chuyện gì đổi khi
có nhiều worker và vì sao cần `zone`.

**Môi trường test.** Docker network riêng, hai backend giả (`tests/fixtures/backend.py`, mỗi bản trả `instance` là tên của
nó), `nginx -t` rồi Nginx `1.30.6` với bản sao cấu hình của bạn mount chỉ đọc. Container tự xoá khi xong; thiếu Docker hoặc
image thì skip. Test kiểm:

1. 40 request `GET /healthz`: đều 200; `olist-api-1` nhận từ 8 tới 12, `olist-api-2` từ 28 tới 32 (tỉ lệ 1:3).
2. `nginx -T` (cấu hình Nginx thực sự nạp) có `server olist-api-1:8000` và `server olist-api-2:8000` trong
   `upstream olist_api`, mỗi dòng có `max_fails=3` và `fail_timeout=30s`, dòng của `olist-api-2` có `weight=3`.
3. Trên một lab mới: gửi 4 request, rồi giết tiến trình backend trong `olist-api-2` (container vẫn chạy, cổng đóng, giống
   app crash), gửi tiếp 20 request `GET /orders/o0` tới `/orders/o19`:
   - cả 20 đều 200;
   - access log có đúng 20 dòng cho chúng; số dòng có IP của `olist-api-2` trong `up=` từ 1 tới 3;
   - 10 dòng cuối không có IP của `olist-api-2`.
4. Chạy starter ban đầu (`tests/fixtures/nginx.starter.conf`): các phép kiểm trên phải bắt được lỗi.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/05-web-server-proxy/exercises/basic/02-upstream-load-balancing -q` pass.
- Đọc error log của Nginx trong lúc test (`connect() failed (111: Connection refused)`, `upstream server temporarily
  disabled`) và giải thích từng dòng.
- Trả lời được: nếu `olist-api-2` treo (nhận kết nối nhưng không trả lời) thay vì chết hẳn, người dùng chịu gì, và
  `proxy_connect_timeout`, `proxy_read_timeout`, `proxy_next_upstream` ảnh hưởng thế nào.
- Nói được vì sao passive health check không thay được active health check, và ai làm active check khi dùng Nginx open source.

## Gợi ý

### Gợi ý 1

Tham số đặt trên từng dòng `server` trong `upstream`: `server host:port weight=N max_fails=N fail_timeout=T;`.

### Gợi ý 2

Request đầu tiên tới backend đã chết không làm người dùng lỗi vì `proxy_next_upstream` mặc định là `error timeout`: Nginx
thử backend kế tiếp trong cùng request. Từ Nginx 1.29.7 (nên cả bản 1.30 dùng ở đây), keep-alive tới upstream bật sẵn và
`proxy_http_version` mặc định là 1.1; cấu hình cũ hay có `keepalive 32; proxy_http_version 1.1; proxy_set_header
Connection "";` là cho các bản trước đó.
