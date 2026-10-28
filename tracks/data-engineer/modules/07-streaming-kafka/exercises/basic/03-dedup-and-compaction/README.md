---
title: Dedup event và mô phỏng log compaction
level: basic
services: []
files:
  - path: starter/dedup.py
    note: 4 TODO
  - path: tests/test_dedup_and_compaction.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/07-streaming-kafka/exercises/basic/03-dedup-and-compaction -q
---

## Mục tiêu

At-least-once delivery nghĩa là consumer sẽ thấy event trùng. Bài này giúp bạn viết dedup theo
`event_id`, đồng thời hiểu log compaction (giữ giá trị mới nhất theo key, tombstone để xoá).

## Đề bài

Hoàn thành `starter/dedup.py`:

1. `dedup_events(events)`: giữ lần xuất hiện **đầu tiên** của mỗi `event_id`, giữ nguyên thứ tự.
   Event không có `event_id` luôn được giữ. Không sửa list đầu vào.
2. `count_duplicates(events)`: dict `event_id → số bản trùng` (lần xuất hiện thứ 2 trở đi), chỉ
   gồm các id có trùng.
3. `compact(records)`: `records` là list `(key, value)` theo thứ tự offset. Trả về dict trạng thái
   cuối: giá trị mới nhất cho mỗi key; value `None` là **tombstone**, xoá key khỏi trạng thái.
4. `compacted_offsets(records)`: các offset (chỉ số trong list) còn lại sau compaction, tức offset
   cuối cùng của mỗi key, sắp tăng dần. Tombstone vẫn được giữ.

Ví dụ: giá sản phẩm `[("p1",10), ("p2",20), ("p1",12.5), ("p3",5), ("p2",None), ("p1",11)]`
compact thành `{"p1": 11, "p3": 5}`, offset còn lại `[3, 4, 5]`.

## Tiêu chí đạt

- `dedup_events` trả đúng thứ tự `e1, e2, e3, (không id)` trên dữ liệu test và không sửa đầu vào.
- `count_duplicates` đếm đúng số bản trùng.
- `compact` xử lý đúng tombstone, kể cả khi key được tạo lại sau tombstone.
- `compacted_offsets` trả đúng offset còn lại.

## Gợi ý

### Gợi ý 1

Dùng một `set` các `event_id` đã thấy. Với compaction, duyệt list một lượt và ghi đè vào dict;
gặp `None` thì `dict.pop(key, None)`.

### Gợi ý 2

Với `compacted_offsets`, duyệt `enumerate(records)` và lưu `last[key] = offset`; kết quả là
`sorted(last.values())`.
