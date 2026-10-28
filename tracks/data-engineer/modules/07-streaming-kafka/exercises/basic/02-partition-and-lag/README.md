---
title: Partitioner, consumer group assignment và consumer lag
level: basic
services: []
files:
  - path: starter/partitioning.py
    note: 5 TODO
  - path: tests/test_partition_and_lag.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/07-streaming-kafka/exercises/basic/02-partition-and-lag -q
---

## Mục tiêu

Hiểu bằng code ba cơ chế cốt lõi của Kafka: key quyết định partition (và vì sao thứ tự chỉ được
giữ trong partition), consumer group chia partition thế nào, và consumer lag được tính ra sao.

## Đề bài

Hoàn thành các hàm trong `starter/partitioning.py`:

1. `partition_for(key, num_partitions, counter=0)`: có key thì `zlib.crc32(key) % num_partitions`;
   key là `None` thì round-robin `counter % num_partitions`; `num_partitions <= 0` thì `ValueError`.
2. `assign(events, num_partitions)`: chia list event (dict) vào partition theo key `order_id`
   (encode UTF-8). Kết quả là dict có đủ key `0..num_partitions-1`, mỗi giá trị là list event theo
   đúng thứ tự xuất hiện. Event không có `order_id` dùng round-robin, `counter` là số thứ tự của
   event không-key (0, 1, 2…).
3. `range_assign(partitions, consumers)`: mô phỏng Range assignor. Sắp xếp consumer theo tên và
   partition tăng dần; mỗi consumer nhận `len(partitions) // len(consumers)` partition liên tiếp,
   `len(partitions) % len(consumers)` consumer đầu nhận thêm một. Consumer dư nhận list rỗng.
   Không có consumer thì `ValueError`.
4. `consumer_lag(end_offsets, committed)`: lag mỗi partition = end offset − committed offset.
   Partition chưa có commit (`None` hoặc thiếu) tính từ 0. Lag không âm.
5. `total_lag(...)`: tổng lag.

## Tiêu chí đạt

- Cùng key luôn ra cùng partition, đúng công thức crc32.
- Event không key được rải round-robin.
- `assign` giữ thứ tự theo từng `order_id` và không để event của một order nằm ở hai partition.
- `range_assign([0..6], ["c1","c2","c3"])` cho `c1:[0,1,2]`, `c2:[3,4]`, `c3:[5,6]`.
- `consumer_lag` đúng với partition chưa commit và không bao giờ âm.

## Gợi ý

### Gợi ý 1

Trong `assign`, khởi tạo `{p: [] for p in range(num_partitions)}` rồi duyệt event một lượt, giữ
một biến đếm riêng cho event không có key.

### Gợi ý 2

Với `range_assign`: `per, extra = divmod(len(parts), len(members))`; consumer thứ `i` nhận
`per + (1 if i < extra else 0)` phần tử, cắt dần từ đầu list partition đã sắp.
