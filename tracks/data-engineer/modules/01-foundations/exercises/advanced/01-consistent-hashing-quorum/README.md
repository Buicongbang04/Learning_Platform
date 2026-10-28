---
title: Consistent hashing và quorum replication kiểu Dynamo
level: advanced
services: []
files:
  - path: starter/ring.py
    note: HashRing và QuorumStore, 9 TODO
  - path: tests/test_ring.py
    note: Không sửa, kiểm tra hợp đồng tối thiểu
run:
  - uv run pytest tracks/data-engineer/modules/01-foundations/exercises/advanced/01-consistent-hashing-quorum -q
---

## Mục tiêu

Tự cài hai cơ chế nền của Cassandra/DynamoDB/Riak: chia dữ liệu bằng consistent hashing có virtual
node, và nhân bản theo quorum (N, R, W) với read repair. Làm xong bạn giải thích được bằng số liệu vì
sao `hash % N` tệ khi thêm máy, và vì sao `R + W > N` cho đọc thấy ghi mới nhất.

## Đề bài

Hoàn thành `starter/ring.py` (hàm `stable_hash` và lớp `QuorumError` đã có sẵn, không đổi).

**`HashRing(nodes=(), vnodes=100)`**

- Mỗi node vật lý có `vnodes` điểm trên vòng, điểm thứ `i` có giá trị `stable_hash(f"{node}#{i}")`.
- `get_node(key)`: node của điểm đầu tiên có hash `>=` `stable_hash(key)`; vượt điểm cuối thì vòng
  về điểm đầu. Vòng rỗng raise `LookupError`.
- `get_nodes(key, n)`: `n` node vật lý **khác nhau** gặp đầu tiên khi đi theo chiều kim đồng hồ
  (bỏ qua vnode của node đã chọn); phần tử đầu là `get_node(key)`. `n` lớn hơn số node raise
  `ValueError`.
- `add_node` (trùng thì `ValueError`), `remove_node` (không có thì `KeyError`), thuộc tính `nodes`.
- Kết quả không phụ thuộc thứ tự thêm node. Tra cứu phải `O(log V)` (V = tổng số vnode), không
  quét tuyến tính.

**`QuorumStore(ring, n=3, r=2, w=2)`**

- Cấu hình sai (`r`/`w` ngoài `[1, n]`, `n` lớn hơn số node) raise `ValueError`.
- `put(key, value)`: replica của key là `ring.get_nodes(key, n)`, bỏ các node trong `self.down`.
  Ít hơn `w` replica sống thì raise `QuorumError` và **không ghi gì**. Ngược lại version mới bằng
  `1 + version lớn nhất trên các replica sống` (0 nếu chưa có), ghi `(version, value)` vào
  `self.data[node][key]` của mọi replica sống, trả version.
- `get(key)`: lấy `r` replica sống đầu tiên theo thứ tự vòng (ít hơn `r` thì `QuorumError`), trả
  value có version cao nhất, `None` nếu không replica nào có key. **Read repair**: replica nào trong
  `r` replica đó đang thiếu hoặc cũ thì ghi bản mới nhất vào.

Ngoài phần code, viết một đoạn ngắn (comment đầu tệp hoặc docstring) trả lời: với 4 node và 20.000
key, thêm node thứ 5 làm di chuyển bao nhiêu phần trăm key với consistent hashing, so với
`hash % N`? Đo bằng code của bạn.

## Tiêu chí đạt

- Toàn bộ test trong `tests/test_ring.py` pass.
- 4 node × 100 vnode: mỗi node nhận 15–35% key; thêm node thứ 5 chỉ di chuyển 10–30% key và mọi key
  di chuyển đều sang node mới; bỏ một node chỉ di chuyển key của node đó.
- Với `N=3, R=2, W=2`: đọc sau khi một replica lỡ một lần ghi vẫn thấy bản mới, và replica cũ được
  sửa. Với `R=W=1`: chứng minh có thể đọc dữ liệu cũ.
- Có số đo so sánh với `hash % N` và giải thích ngắn.
- Code có type hints, không quét tuyến tính toàn vòng cho mỗi lần `get_node`.

## Gợi ý

### Gợi ý 1

Giữ một list các điểm hash **đã sắp xếp** và một dict `điểm → node`.
`bisect.bisect_left(points, h) % len(points)` cho vị trí điểm đầu tiên `>= h`, phép `%` xử lý việc
vòng về đầu. Thêm điểm bằng `bisect.insort`.

### Gợi ý 2

`get_nodes`: từ vị trí bắt đầu, đi tiếp `(start + i) % len(points)` và gom node chưa có trong danh
sách cho tới khi đủ `n`. Với `QuorumStore`, viết hàm phụ `_live_replicas(key)` dùng chung cho `put`
và `get`; kiểm tra quorum *trước* khi ghi để thất bại không để lại dữ liệu.
