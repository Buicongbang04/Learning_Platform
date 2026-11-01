---
title: Bảo vệ upstream - rate limit, cache và timeout
level: intermediate
services: []
files:
  - path: starter/nginx.conf
    note: 5 TODO
  - path: tests/test_protect_upstream.py
    note: Không sửa
  - path: tests/fixtures/backend.py
    note: Backend giả của Olist Shop
run:
  - docker pull nginx:1.30.6-alpine && docker pull python:3.12.16-alpine3.24
  - uv run pytest tracks/devops/modules/05-web-server-proxy/exercises/intermediate/03-protect-upstream -q
---

## Mục tiêu

Dùng Nginx để API của Olist Shop sống sót qua ba thứ hay giết backend: một client gọi endpoint đắt tiền liên tục, một
endpoint đọc nhiều mà dữ liệu ít đổi, và một request treo lâu giữ chặt kết nối.

## Đề bài

`POST /jobs/recompute` đẩy một job tính lại doanh thu vào Redis; gọi dồn dập sẽ làm đầy hàng đợi của worker.
`GET /stats/revenue-by-state` đọc bảng do worker tính, dữ liệu chỉ đổi vài phút một lần nhưng dashboard của 200 người bán
gọi nó liên tục. Một số request chậm bất thường giữ kết nối tới 60 giây (mặc định của Nginx). Sửa `starter/nginx.conf`:

| Mục | Yêu cầu |
| --- | --- |
| Rate limit | `location /jobs/`: theo IP client (`$binary_remote_addr`), `rate=1r/s`, `burst=5 nodelay`, vượt thì trả `429` (mặc định của Nginx là `503`) |
| Cache | `location = /stats/revenue-by-state`: cache response 200 trong 30 giây ở `/var/cache/nginx/olist` (`keys_zone=olist_cache:10m`, `max_size=100m`, `inactive=10m`); header `X-Cache-Status` trên response; request có header `X-Cache-Bypass` khác rỗng và khác `0` thì bỏ qua bản cache, lấy bản mới từ backend và lưu bản mới đó vào cache |
| Timeout | Tới upstream: kết nối tối đa 2 giây, chờ response tối đa 3 giây (`proxy_read_timeout 3s`) |
| Phạm vi | Route khác (`/orders/...`) không bị rate limit và không bị cache |

**Môi trường test.** Một backend giả (`tests/fixtures/backend.py`; mỗi response có trường `served` là lần thứ mấy backend
phục vụ path đó, `GET /slow?seconds=N` ngủ N giây rồi trả lời), `nginx -t`, rồi Nginx `1.30.6` với bản sao cấu hình của
bạn. Mọi request của test đến từ cùng một IP. Test kiểm:

1. **Rate limit**: 15 `POST /jobs/recompute` liên tiếp nhanh nhất có thể: 6 cái đầu là 202; có ít nhất 5 cái 429; không có
   mã nào khác 202 và 429. Sau đó 20 `GET /orders/o42` liên tiếp đều 200. Giới hạn 1 request/giây có biên rộng: dù máy chậm
   tới mức 15 request mất 4 giây, vẫn còn đủ 5 mã 429.
2. **Cache**: bốn `GET /stats/revenue-by-state` lần lượt: `MISS`, `HIT` (cùng `served` với lần đầu), có
   `X-Cache-Bypass: 1` thì `BYPASS` (`served` tăng 1), rồi `HIT` trả đúng bản vừa lấy khi bypass. Hai `GET /orders/o7`
   liên tiếp có `served` khác nhau và không có `X-Cache-Status: HIT`.
3. **Timeout**: `GET /slow?seconds=6` nhận `504` sau 2,5 tới 5,5 giây; `GET /slow?seconds=1` nhận 200.
4. Chạy starter ban đầu (`tests/fixtures/nginx.starter.conf`): ba nhóm kiểm trên phải bắt được lỗi.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/05-web-server-proxy/exercises/intermediate/03-protect-upstream -q` pass.
- Tính được: với `rate=1r/s burst=5 nodelay`, một client gửi 100 request trong 10 giây được bao nhiêu cái qua; bỏ `nodelay`
  thì khác gì với độ trễ người dùng thấy.
- Giải thích vì sao rate limit theo `$binary_remote_addr` sai hoàn toàn khi Nginx đứng sau load balancer mà chưa cấu hình
  `real_ip`, và vì sao nhiều người dùng sau cùng một NAT công ty có thể bị chặn oan.
- Nêu ba loại response không bao giờ được cache ở reverse proxy, và Nginx mặc định làm gì với response có `Set-Cookie`.

## Gợi ý

### Gợi ý 1

`limit_req_zone` và `proxy_cache_path` đặt ở mức `http`; `limit_req`, `limit_req_status`, `proxy_cache`,
`proxy_cache_valid`, `proxy_cache_bypass` đặt trong `location`. Biến `$upstream_cache_status` cho giá trị `MISS`, `HIT`,
`BYPASS`, `EXPIRED`, `STALE`...

### Gợi ý 2

`proxy_cache_bypass` nhận danh sách biến: chỉ cần một biến khác rỗng và khác `"0"` là bỏ qua cache. Đừng nhầm với
`proxy_no_cache` (không lưu response). `add_header ... always` để header có cả trên response lỗi. `proxy_cache_lock on`
và `proxy_cache_use_stale updating` chống dồn request khi bản cache vừa hết hạn.
