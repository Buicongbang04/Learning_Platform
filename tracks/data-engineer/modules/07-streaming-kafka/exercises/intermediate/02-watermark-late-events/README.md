---
title: Watermark và xử lý event đến trễ
level: intermediate
services: []
files:
  - path: starter/watermark.py
    note: 5 TODO
  - path: tests/test_watermark_late_events.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/07-streaming-kafka/exercises/intermediate/02-watermark-late-events -q
---

## Mục tiêu

Hiểu và tự cài đặt cơ chế watermark: khi nào một window theo event time được coi là xong để phát
kết quả, event lệch thứ tự được chấp nhận tới đâu, và event quá trễ đi đâu.

## Đề bài

Hoàn thành lớp `TumblingWindowProcessor(size, allowed_lateness)` trong `starter/watermark.py`.
Event là dict `{"event_time": int, "key": str, "amount": float}`.

1. `watermark`: `None` khi chưa có event; ngược lại `max_event_time − allowed_lateness`.
   Watermark không bao giờ lùi (event cũ không làm giảm `max_event_time`).
2. `process(event)`:
   - Tính window `[s, s + size)` của event.
   - Nếu watermark hiện tại (trước khi tính event này) đã có và `s + size <= watermark` thì event là
     **late**: thêm vào `self.late_events`, không cộng vào kết quả, trả về `[]`.
   - Ngược lại cộng `count` và `total` vào state của `(s, key)`, cập nhật `max_event_time`.
   - Phát (trả về và xoá khỏi state) mọi window có `window_end <= watermark` mới. Mỗi kết quả là
     `{"window_start", "window_end", "key", "count", "total"}`, `total` làm tròn 2 chữ số, sắp theo
     `(window_start, key)`.
3. `flush()`: kết thúc stream, phát mọi window còn trong state (cùng định dạng, cùng thứ tự).
4. Hàm `run(events, size, allowed_lateness)`: chạy cả list event rồi flush, trả về
   `(mọi kết quả đã phát, late_events)`.

## Tiêu chí đạt

- Window chỉ được phát khi watermark ≥ cuối window, và mỗi window chỉ phát một lần.
- Event lệch thứ tự nhưng window chưa đóng vẫn được tính.
- Event thuộc window đã đóng vào `late_events`, không làm đổi kết quả.
- Trên cùng một stream, `allowed_lateness=0` bỏ 2 event còn `allowed_lateness=120` giữ đủ 6 event.

## Gợi ý

### Gợi ý 1

State là dict `(window_start, key) -> [count, total]`. Hàm phát kết quả duyệt `sorted(self._state)`
và `pop` các window đủ điều kiện. Viết một hàm `_emit(ready)` nhận điều kiện để dùng chung cho
`process` (end ≤ watermark) và `flush` (luôn đúng).

### Gợi ý 2

Thứ tự trong `process` quan trọng: kiểm tra late với watermark **cũ**, rồi mới cộng state và cập
nhật `max_event_time`, cuối cùng phát theo watermark **mới**. Nếu cập nhật trước thì một event rất
mới có thể tự coi mình là late.
