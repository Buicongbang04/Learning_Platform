---
title: Sink exactly-once từ Kafka vào SQL bằng offset trong cùng transaction
level: advanced
services: []
files:
  - path: starter/sink.py
    note: 5 TODO
  - path: tests/test_exactly_once_sink.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/07-streaming-kafka/exercises/advanced/01-exactly-once-sink -q
---

## Mục tiêu

Kafka transactions chỉ bao trọn Kafka → Kafka. Khi đích là database, bạn phải tự đạt
"effectively exactly-once". Bài này giúp bạn thiết kế sink vừa idempotent vừa lưu offset nguyên tử
cùng dữ liệu, chịu được retry, crash giữa batch, replay và event lệch thứ tự.

## Đề bài

Consumer đọc topic `olist.orders` và chuyển từng batch record cho `OrderSink.process_batch`. Sink
ghi vào SQLite (đại diện cho PostgreSQL/warehouse), và khi consumer khởi động lại nó sẽ `seek()`
tới `committed_offsets()` của sink thay vì offset trong Kafka.

Hoàn thành lớp `OrderSink` trong `starter/sink.py` (docstring mô tả đủ hợp đồng):

1. `init_schema()`: tạo bảng, gọi lại nhiều lần không lỗi.
2. `process_batch(records, fail_after=None)`: áp dụng cả batch trong **một transaction**:
   - bỏ record có offset nhỏ hơn `next_offset` đã lưu của `(topic, partition)`;
   - bỏ `event_id` đã xử lý (trùng do producer retry ở offset khác);
   - upsert `orders` theo `order_id`, chỉ ghi đè khi `event_time` mới hơn bản đang lưu;
   - lưu `next_offset = max offset + 1` cho từng partition trong batch;
   - `fail_after=n` giả lập crash sau `n` record: raise `RuntimeError`, không thay đổi nào được lưu;
   - trả về số record được áp dụng (không tính record bị bỏ vì offset cũ hoặc event_id trùng).
3. `committed_offsets()`, `order_status(order_id)`, `gmv_by_state()` (bỏ đơn đang `canceled`).

Bạn tự chọn schema, câu SQL, cách tổ chức code. Ngoài test, hãy viết vài dòng (comment ở đầu tệp
hoặc ghi chú riêng) trả lời: cách này có còn đúng khi chạy nhiều consumer song song không, và khi
chuyển sang PostgreSQL cần đổi gì.

## Tiêu chí đạt

- Mọi test trong `tests/test_exactly_once_sink.py` pass.
- Replay cùng batch, crash rồi retry, hay nhận lại dữ liệu chồng lấn sau restart đều cho cùng kết quả GMV và offset.
- Event cũ đến muộn không làm lùi trạng thái đơn.
- Dữ liệu và offset luôn được commit cùng nhau (không bao giờ có offset mới mà thiếu dữ liệu hoặc ngược lại).
- Có giải thích ngắn về giới hạn của thiết kế.

## Gợi ý

### Gợi ý 1

Trong `sqlite3`, `with conn:` mở một transaction ngầm, commit khi khối kết thúc bình thường và
rollback khi có exception. Đặt mọi câu ghi (orders, processed_events, consumer_offsets) trong cùng
một khối `with`.

### Gợi ý 2

`INSERT OR IGNORE INTO processed_events ...` rồi xem `cursor.rowcount` để biết event mới hay trùng.
Upsert có điều kiện: `INSERT ... ON CONFLICT(order_id) DO UPDATE SET ... WHERE excluded.event_time > orders.event_time`.
Offset cập nhật bằng `MAX(next_offset, excluded.next_offset)` để không bao giờ lùi.
