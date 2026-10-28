---
title: Tumbling và hopping window cho GMV theo bang
level: intermediate
services: []
files:
  - path: starter/windows.py
    note: 4 TODO
  - path: tests/test_windowed_aggregation.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/07-streaming-kafka/exercises/intermediate/01-windowed-aggregation -q
---

## Mục tiêu

Tự cài đặt logic windowing theo event time mà Flink, Kafka Streams hay Spark làm bên trong:
gán event vào tumbling/hopping window rồi aggregate theo key.

## Đề bài

Event là dict có `event_time` (số nguyên giây), `customer_state`, `amount`. Hoàn thành
`starter/windows.py`:

1. `tumbling_window_start(ts, size)`: điểm bắt đầu window chứa `ts` (`ts - ts % size`).
   `size <= 0` thì `ValueError`.
2. `hopping_window_starts(ts, size, advance)`: list tăng dần mọi `s` sao cho `s % advance == 0`,
   `s >= 0` và `s <= ts < s + size`. Yêu cầu `0 < advance <= size`, sai thì `ValueError`.
   Ví dụ `hopping_window_starts(725, 300, 60) == [480, 540, 600, 660, 720]`.
3. `tumbling_aggregate(events, size, key_field="customer_state", value_field="amount")`: trả về list
   dict `{"window_start", "window_end", "key", "count", "sum"}`, một dòng cho mỗi cặp
   (window, key) có dữ liệu, `sum` làm tròn 2 chữ số, sắp theo `(window_start, key)`. Kết quả không
   phụ thuộc thứ tự event đầu vào.
4. `hopping_aggregate(events, size, advance, ...)`: như trên nhưng mỗi event được tính vào mọi
   hopping window chứa nó.

## Tiêu chí đạt

- Biên window đúng: `event_time=60` thuộc window `[60, 120)`, không thuộc `[0, 60)`.
- `tumbling_aggregate` đúng count/sum trên dữ liệu test và không phụ thuộc thứ tự đầu vào.
- `hopping_aggregate` với `size=120, advance=60` đếm mỗi event ở 2 window (trừ event trước giây 60).
- `hopping_aggregate(e, 60, 60) == tumbling_aggregate(e, 60)`.
- Đối số không hợp lệ ném `ValueError`.

## Gợi ý

### Gợi ý 1

Dùng `collections.defaultdict` với key là tuple `(window_start, key)` và giá trị `[count, sum]`.
Cuối cùng sắp `sorted(acc.items())` là được thứ tự `(window_start, key)`.

### Gợi ý 2

Window hopping cuối cùng chứa `ts` bắt đầu tại `last = ts - ts % advance`. Window đầu tiên bắt đầu
tại `last - size + advance` (không nhỏ hơn 0). Duyệt `range(first, last + 1, advance)`. Viết một hàm
aggregate chung nhận các cặp `(window_start, event)` để dùng cho cả tumbling và hopping.
