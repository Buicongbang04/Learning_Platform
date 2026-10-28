# Lời giải: Watermark và xử lý event đến trễ

## Cách làm

- `watermark` là property tính từ `max_event_time` và `allowed_lateness`.
- `process`: tính `start = ts - ts % size`; nếu `start + size <= watermark` (watermark cũ) thì ghi
  vào `late_events` và trả `[]`. Ngược lại cộng vào `_state[(start, key)]`, cập nhật
  `max_event_time = max(...)`, rồi `_emit(end <= watermark)`.
- `_emit(ready)` duyệt các key đã sắp, `pop` window thoả điều kiện nên mỗi window chỉ phát một lần.
- `flush` gọi `_emit` với điều kiện luôn đúng. `run` nối mọi thứ lại.

## Vì sao

- **Watermark là đánh đổi giữa độ trễ và độ đầy đủ.** Test `test_run_tradeoff_lateness` cho thấy:
  lateness 0 phát kết quả ngay nhưng bỏ 2/6 event; lateness 120 giây giữ đủ nhưng window `[0, 60)`
  chỉ được phát khi đã thấy event ở giây 200. Trong thực tế chọn lateness dựa trên phân phối độ trễ
  quan sát được (vd. p99 của `ingest_time − event_time`).
- **State được xoá khi window đóng**, nên bộ nhớ có giới hạn. Không có watermark thì state tăng mãi.
- **Watermark chỉ tiến, không lùi**: event cũ không làm đổi watermark, nếu không window đã phát có
  thể "mở lại".
- **Late event không bị vứt im lặng**: đưa vào side output (trong Kafka là topic
  `olist.orders.late` hoặc DLQ) để đếm, alert và xử lý bù bằng batch. Flink gọi là
  `sideOutputLateData`, Spark thì bỏ qua late data dưới watermark.
- Watermark trong thực tế được tính **theo từng partition** rồi lấy **min** khi gộp, vì một partition
  chậm không được để các partition nhanh đóng window sớm. Partition rảnh (idle) cần cơ chế
  `withIdleness` để không giữ watermark đứng yên mãi.
