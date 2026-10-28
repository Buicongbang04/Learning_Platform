# Lời giải: Job Reverse ETL đồng bộ khách hàng sang CRM giả

Xem `sync.py` cùng thư mục.

## Model nguồn

- Gom theo `customer_unique_id`: trong Olist mỗi đơn sinh một `customer_id` mới, nên muốn biết khách quay lại phải
  dùng `customer_unique_id`. Đây là **external ID** ổn định để upsert ở CRM.
- Tổng tiền mỗi đơn tính ở CTE `order_value` trước, rồi `LEFT JOIN`. Đếm đơn bằng `COUNT(DISTINCT)`.
- `arg_max(customer_state, order_purchase_timestamp)` lấy state mới nhất (khách có thể chuyển nhà).
- Segment tính trong Python cho dễ đọc. Trong dự án thật nên để trong dbt model để dashboard và CRM cùng một định
  nghĩa.

## Bốn tính chất của job

1. **Change detection.** `state` lưu `external_id → hash` của lần gửi thành công gần nhất. Hash dùng JSON có
   `sort_keys` để thứ tự key không làm đổi hash. Chỉ record mới hoặc đổi mới được gửi, nên số call API tỉ lệ với số
   thay đổi chứ không với kích thước bảng.
2. **Idempotent upsert.** CRM upsert theo `external_id`, nên gửi lại một record không tạo trùng. Kết hợp với diff,
   chạy lại job bao nhiêu lần cũng an toàn.
3. **Retry có chọn lọc.** `TransientError` (429, 5xx) retry với exponential backoff `0.5, 1, 2…` giây; production
   thêm jitter để nhiều worker không cùng dội lại một lúc. `PermanentError` (400) không retry vì kết quả sẽ y hệt;
   record được ghi vào `failed_ids` để người vận hành xem.
4. **Ghi state sau khi thành công.** Nếu batch 2 lỗi, state chỉ có batch 1. Lần chạy sau diff tự tìm ra phần còn
   thiếu. Đây là cách đạt "at-least-once + idempotent = effectively-once".

## Đưa vào production

- Lưu `state` trong bảng của warehouse (`_sync_state(external_id, hash, synced_at)`) hoặc Postgres, không để trong
  bộ nhớ.
- Ghi log mỗi lần chạy: total/sent/skipped/failed, thời gian, và alert khi tỉ lệ lỗi vượt ngưỡng.
- Tôn trọng rate limit của API (token bucket) ngoài retry.
- Xử lý xoá: khách rời segment thì `mirror` (xoá ở CRM) hay giữ nguyên, phải được quyết định rõ.
- Chỉ gửi field cần thiết và kiểm tra consent (module 10).
- Khi có nhiều đích, cân nhắc Hightouch/Census thay vì tự bảo trì connector.
