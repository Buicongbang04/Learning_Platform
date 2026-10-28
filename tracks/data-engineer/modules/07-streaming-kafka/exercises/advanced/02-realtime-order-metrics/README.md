---
title: Stream processor GMV theo phút theo bang cho order events Olist
level: advanced
services: []
files:
  - path: starter/processor.py
    note: 5 TODO
  - path: tests/test_realtime_order_metrics.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/07-streaming-kafka/exercises/advanced/02-realtime-order-metrics -q
---

## Mục tiêu

Ghép mọi mảnh của module thành một stream processor hoàn chỉnh: parse và validate, dead-letter
queue, dedup có TTL, tumbling window theo event time, watermark, late events và metric vận hành.
Đây là lõi của milestone m07 trong capstone.

## Đề bài

Dashboard vận hành của Olist cần "số đơn mới, GMV và số đơn huỷ theo phút, theo bang". Order events
đến từ topic `olist.orders` dưới dạng bytes JSON (xem docstring trong `starter/processor.py`).

Hoàn thành `OrderMetricsProcessor` (thuần Python, không phụ thuộc Kafka, để test offline):

1. **Parse + validate**: JSON object có đủ `event_id, order_id, status, amount, customer_state,
   event_time`; `status` hợp lệ; `amount` là số không âm (không phải bool); `event_time` là số
   nguyên. Sai thì ghi `{"raw": raw, "reason": "..."}` vào `self.dlq`.
2. **Dedup theo `event_id`** với bộ nhớ có TTL: quên các id có `event_time < max_event_time − dedup_ttl`.
   Trùng thì tăng `self.duplicates`.
3. **Late events**: window của event có `end <= watermark` hiện tại thì ghi vào `self.late`.
4. **Tumbling window** theo `window_size`, key `customer_state`: `orders` và `gmv` từ event
   `created`, `canceled` từ event `canceled`, các trạng thái khác chỉ đẩy watermark.
5. **Phát kết quả** khi `watermark = max_event_time − allowed_lateness` vượt cuối window; `flush()`
   phát phần còn lại; `stats()` trả số window đã phát, duplicates, late, dlq.

Phần mở rộng (không chấm bằng test, chấm theo rubric): viết hàm `run(bootstrap, in_topic, out_topic)`
nối processor với `KafkaConsumer`/`KafkaProducer` (`kafka-python-ng`): đọc `olist.orders`, ghi kết
quả lên `olist.gmv_per_minute` với key `"{window_start}:{customer_state}"`, ghi DLQ lên
`olist.orders.dlq`, commit offset sau khi đã gửi kết quả. Nêu rõ semantics đạt được.

## Tiêu chí đạt

- Mọi test trong `tests/test_realtime_order_metrics.py` pass.
- Message hỏng không làm processor dừng, có lý do lỗi rõ ràng.
- Bộ nhớ dedup và state window có giới hạn (được dọn theo TTL và khi window đóng).
- Có phân tích đánh đổi: `allowed_lateness`, `dedup_ttl`, khi restart processor thì state mất (cần checkpoint).
- (Mở rộng) Có hàm `run` nối Kafka, mô tả được at-least-once và cách đầu ra idempotent theo key.

## Gợi ý

### Gợi ý 1

Tách một hàm `parse(raw) -> dict` ném `ValueError(reason)`; `process` chỉ cần
`try/except ValueError`. Nhớ `isinstance(True, int)` là `True` trong Python.

### Gợi ý 2

Tái dùng cấu trúc của bài intermediate 02 (state dict + `_emit(ready)`). Dọn bộ nhớ dedup khi
`max_event_time` tăng. Đếm `emitted_windows` ngay trong `_emit` để `stats()` đúng cả với `flush()`.
