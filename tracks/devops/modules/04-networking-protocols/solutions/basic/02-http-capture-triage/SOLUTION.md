# Lời giải: đọc transcript curl -v

Code đầy đủ ở `http_triage.py` cạnh tệp này.

## Cách làm

1. **Hai hàm nhỏ làm phần lớn việc**: `headers()` (tên chữ thường, header lặp thì nối bằng `, ` như RFC 9110 cho phép) và
   `cache_directives()` (directive thành dict, giá trị có thể có ngoặc kép).
2. **`cache_state` là một chuỗi `if` theo đúng thứ tự trong đề**, trả về ngay ở điều kiện đầu tiên. Đổi thứ tự là đổi
   nghĩa: `no-store` thắng mọi thứ; `private` và quy tắc `Authorization` đứng trước `no-cache` vì chúng cấm cache dùng
   chung lưu lại, còn `no-cache` cho lưu nhưng bắt hỏi lại.
3. **Ngày tháng**: `parsedate_to_datetime` trả datetime có múi giờ (GMT), hiệu hai ngày không phụ thuộc giờ máy.
4. **`keep_alive`** đi theo phiên bản: HTTP/1.0 mặc định đóng, HTTP/1.1 mặc định giữ, HTTP/2 luôn là một kết nối
   multiplex nhiều stream (header `Connection` bị cấm trong HTTP/2).

## Từng transcript nói gì

| Transcript | Ý nghĩa vận hành |
| --- | --- |
| `static_asset_h2.txt` | Asset có hash trong tên: `max-age` 1 năm + `immutable`, CDN giữ thêm `31536000 - Age`. Deploy bản mới đổi tên tệp, không cần purge |
| `api_orders_private.txt` | `private`: chỉ trình duyệt được cache. `Vary: Authorization` không thay được `private` cho cache dùng chung |
| `api_auth_no_cc_public.txt` | Request có `Authorization`, response chỉ có `max-age`: cache dùng chung **không** được lưu (RFC 9111 mục 3.5). Một CDN cấu hình "cache mọi thứ" bỏ qua quy tắc này sẽ trả `/v1/me` của người A cho người B: một trong các sự cố rò dữ liệu kinh điển |
| `catalog_s_maxage.txt` | `s-maxage` cho CDN giữ 10 phút trong khi trình duyệt chỉ giữ 1 phút: CDN chịu tải, client vẫn thấy dữ liệu khá mới |
| `legacy_expires_http10.txt` | Server cũ dùng `Expires` tuyệt đối. Tính theo `Expires - Date` (đồng hồ của server), không theo giờ máy bạn. HTTP/1.0 không keep-alive: mỗi request một kết nối TCP mới |
| `checkout_503_no_store.txt` | 503 có `Retry-After: 120` nhưng là `POST /checkout` không có idempotency key: retry tự động có thể tạo hai đơn. Thêm `Idempotency-Key` ở client và lưu kết quả theo key ở server |
| `payment_429_http_date.txt` | 429 với `Retry-After` dạng ngày; có `Idempotency-Key` nên retry an toàn sau 30 giây |
| `order_502_gateway.txt` | 502 từ Nginx: upstream chết hoặc trả rác. GET là idempotent, retry được (có backoff). Module 05 có bài sự cố 502 |
| `index_no_cache_etag.txt` | `no-cache` + `ETag`: cache được lưu nhưng mỗi lần phải hỏi lại bằng `If-None-Match`, server trả 304 nếu không đổi. Đúng cho HTML trỏ tới asset có hash |
| `banner_stale_age.txt` | `Age` 90 > `max-age` 60: cache đã giữ quá hạn. Có thể do `stale-while-revalidate` hoặc do origin chậm; nhìn `Age` là cách nhanh nhất để biết response đến từ cache |

## Lưu ý về các quy tắc đã đơn giản hoá

- Bài bỏ qua heuristic freshness (RFC 9111 mục 4.2.2): cache được phép tự đoán thời gian tươi từ `Last-Modified` khi không
  có `max-age`/`Expires`. Nhiều CDN làm vậy, nên "không đặt `Cache-Control`" không có nghĩa là "không cache".
- Danh sách mã retry là lựa chọn vận hành phổ biến, không phải quy định của RFC. 500 đôi khi là lỗi tạm thời; retry 500
  một lần với backoff là chấp nhận được nếu thao tác idempotent.
