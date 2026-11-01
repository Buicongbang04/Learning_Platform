---
title: Đọc transcript curl -v - retry an toàn, cache dùng chung, keep-alive
level: basic
services: []
files:
  - path: starter/http_triage.py
    note: 3 hàm có TODO
  - path: tests/test_http_triage.py
    note: Không sửa
  - path: tests/fixtures/catalog_s_maxage.txt
    note: Một transcript mẫu, đọc để hiểu dạng dữ liệu
run:
  - uv run pytest tracks/devops/modules/04-networking-protocols/exercises/basic/02-http-capture-triage -q
---

## Mục tiêu

Đọc một trao đổi HTTP thô và trả lời ba câu hỏi vận hành hay bị trả lời sai: client có được tự retry không (và chờ bao
lâu), CDN hay reverse proxy dùng chung có được giữ response này không và giữ thêm bao lâu, kết nối có được tái dùng không.

## Đề bài

`tests/fixtures/` có 10 transcript `curl -v` thu từ Olist Shop: dòng `* ` là thông tin của curl, dòng `> ` là request
gửi đi, dòng `< ` là response nhận về, dòng `{ [...]` là body (bỏ qua). Hàm `split_transcript` đã viết sẵn tách hai phần
request và response. Viết `analyze(text)` trong `starter/http_triage.py`, trả `dict` đúng 8 khoá:

| Khoá | Quy tắc |
| --- | --- |
| `method` | Từ đầu tiên của dòng request đầu tiên, chữ hoa |
| `version` | Từ đầu tiên của dòng response đầu tiên, chữ hoa: `HTTP/1.0`, `HTTP/1.1`, `HTTP/2` |
| `status` | Mã trạng thái (`int`) ở dòng response đầu tiên |
| `retry_safe` | `True` khi **cả hai**: `status` thuộc `{408, 429, 502, 503, 504}`, **và** `method` thuộc `{GET, HEAD, OPTIONS, PUT, DELETE}` hoặc request có header `Idempotency-Key`. Ngược lại `False`. `500` không nằm trong danh sách: thường là bug, retry cho kết quả y hệt |
| `retry_after` | Không có header `Retry-After`: `None`. Giá trị toàn chữ số: số giây đó. Giá trị là HTTP-date: số giây từ header `Date` của response tới ngày đó (làm tròn xuống, âm thì `0`); không có `Date` thì `None` |
| `cache` | Một trong `no-store`, `private`, `revalidate`, `none`, `fresh`, `stale`, theo quy tắc dưới |
| `ttl` | `int` khi `cache` là `fresh` (số giây còn tươi) hoặc `stale` (`0`); các trường hợp khác `None` |
| `keep_alive` | `HTTP/2`: `True`. `HTTP/1.1`: `True` trừ khi header `Connection` của response có token `close`. `HTTP/1.0`: `False` trừ khi `Connection` có token `keep-alive`. So sánh token không phân biệt hoa thường |

`cache` mô tả hành vi của một **cache dùng chung** (CDN, Nginx `proxy_cache`), xét theo đúng thứ tự, gặp điều kiện đầu
tiên thì dừng (`Cache-Control` là header của response; directive so sánh không phân biệt hoa thường):

1. `Cache-Control` có `no-store` → `no-store`.
2. `Cache-Control` có `private` → `private`.
3. Request có header `Authorization` và `Cache-Control` của response không có `public`, `s-maxage` hay
   `must-revalidate` → `private` (RFC 9111 mục 3.5: cache dùng chung không được lưu response cho request có xác thực
   nếu server không cho phép rõ ràng).
4. `Cache-Control` có `no-cache` → `revalidate` (được lưu nhưng phải hỏi lại server trước mỗi lần dùng).
5. Thời gian tươi (freshness lifetime): `s-maxage` nếu có, không thì `max-age`, không thì `Expires` trừ `Date` (giây,
   âm hoặc ngày không đọc được thì `0`). Không có cả ba → `none` (bài này không dùng heuristic freshness).
6. Còn lại = thời gian tươi trừ header `Age` (không có `Age` thì `0`). Còn lại `> 0` → `fresh` với `ttl` bằng số còn
   lại; ngược lại → `stale` với `ttl = 0`.

Tên header không phân biệt hoa thường (HTTP/2 luôn viết thường). Ngày tháng trong HTTP luôn là GMT; dùng
`email.utils.parsedate_to_datetime`, đừng dùng giờ máy. Test chạy hàm trên 10 transcript và 6 biến thể sửa từ chúng.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/04-networking-protocols/exercises/basic/02-http-capture-triage -q` pass.
- Giải thích được vì sao `checkout_503_no_store.txt` có `Retry-After` mà client vẫn **không** được tự retry, và cần
  thêm gì để retry được.
- Nói được rủi ro nếu một CDN lưu `api_auth_no_cc_public.txt` (`/v1/me` của người này trả cho người khác) và sửa ở đâu:
  ứng dụng gửi `Cache-Control: private` hoặc `no-store`, CDN không cache đường dẫn có `Authorization`.

## Gợi ý

### Gợi ý 1

Viết `headers()` trước: bỏ dòng đầu, `partition(":")` từng dòng, tên chữ thường. Rồi `cache_directives()`: tách theo
`,`, mỗi phần `partition("=")`. Hai hàm nhỏ này làm phần còn lại thành vài `if`.

### Gợi ý 2

`max-age` là tuổi tối đa tính từ lúc server tạo response, còn `Age` là số giây response đã nằm trong các cache phía trước.
Vì vậy cache tiếp theo chỉ được giữ thêm `max-age - Age`. Với `Retry-After` dạng ngày, lấy hiệu của hai lần
`parsedate_to_datetime(...)` rồi `int(delta.total_seconds())`.
