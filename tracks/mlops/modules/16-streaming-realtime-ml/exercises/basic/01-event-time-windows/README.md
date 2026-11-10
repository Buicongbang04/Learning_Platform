---
title: Cửa sổ theo event time, watermark, sự kiện trễ và trùng lặp
level: basic
services: []
files:
  - path: starter/windows.py
    note: 5 TODO
  - path: quiz.yaml
    note: 8 câu về stream processing
  - path: tests/test_windows.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/16-streaming-realtime-ml/exercises/basic/01-event-time-windows -q
---

## Mục tiêu

Tự viết phần lõi mà Flink hay Spark Structured Streaming làm cho bạn: gán sự kiện vào cửa sổ theo **event time**, giữ watermark,
quyết định sự kiện nào trễ quá mức để bỏ, và không đếm hai lần một sự kiện bị gửi lại. Viết bằng Python thuần trên list sự kiện để
chấm nhanh; bài Intermediate 01 đặt đúng logic này lên một topic Kafka thật.

## Đề bài

Mỗi sự kiện là dict `{"event_id": str, "key": str|int, "ts": int, "value": float}`, `ts` là event time (giây epoch). Điền
`starter/windows.py`:

1. `tumbling_start(ts, size)`: mốc bắt đầu cửa sổ tumbling chứa `ts`, tức `ts - ts % size`.
2. `sliding_windows(ts, size, step)`: mọi cửa sổ nửa mở `[start, start + size)` có `start` chia hết cho `step` và chứa `ts`,
   trả list tuple `(start, end)` tăng dần theo `start`.
3. `session_windows(timestamps, gap)`: mỗi sự kiện mở khoảng `[ts, ts + gap)`; hai khoảng gối lên nhau (sự kiện sau có
   `ts < end` hiện tại, so sánh chặt) thì gộp. Trả list `(start, end)` tăng dần; input có thể chưa sắp xếp.
4. `WindowAggregator(size, lateness)` gộp cửa sổ tumbling theo `key`. `add(event)` xử lý một sự kiện theo đúng thứ tự:
   - `event_id` đã gặp (dù lần trước được nhận hay bị bỏ vì trễ) thì tăng `duplicates`, trả `[]`.
   - Sự kiện **trễ** khi watermark hiện tại (trước sự kiện này) khác `None` và `window_end <= watermark`: tăng `late`, trả `[]`.
   - Ngược lại cộng vào cửa sổ của nó: `count += 1`, `total += value`.
   - Cập nhật `watermark = max(watermark, ts - lateness)` (lần đầu là `ts - lateness`).
   - Trả mọi cửa sổ đang mở có `window_end <= watermark` (đóng và xoá khỏi trạng thái), sắp theo `(window_end, key)`.
5. `flush()`: đóng mọi cửa sổ còn mở, cùng thứ tự; gọi lần hai trả `[]`.

Mỗi dòng trả về là dict đúng năm khoá `{"key", "window_start", "window_end", "count", "total"}`; thuộc tính `watermark`,
`late`, `duplicates` đọc được từ ngoài.

Test có các ca viết tay (trễ trong và ngoài `lateness`, trùng lặp, thứ tự xuất) và ba luồng sinh ngẫu nhiên 700 sự kiện bị lệch
thứ tự, có sự kiện trễ 25 phút và 40 bản gửi lại; mỗi luồng so số đếm, tổng, **và thời điểm cửa sổ được đóng** (sự kiện nào làm nó
đóng) với một bản tham chiếu trong test.

Làm thêm `quiz.yaml` (8 câu, đáp án ở `solutions/`).

## Tiêu chí đạt

- Test pass.
- Bạn giải thích được vì sao `lateness` lớn làm feature đúng hơn nhưng chậm hơn, và điều gì xảy ra với sự kiện đến sau khi cửa sổ
  của nó đã đóng.
- Bạn nói được vì sao chống trùng phải chạy trước kiểm tra trễ (gợi ý: đếm sai loại lỗi thì cảnh báo sai chỗ).

## Gợi ý

### Gợi ý 1

Giữ trạng thái `dict[(key, window_start)] -> dòng đang mở` và `set` các `event_id` đã gặp. `flush` và đóng cửa sổ trong `add`
dùng chung một hàm phụ nhận điều kiện.

### Gợi ý 2

Watermark chỉ tăng. Sự kiện trễ có `ts < window_end <= watermark` nên không bao giờ kéo watermark lên, bạn không cần trường hợp
riêng cho nó.
