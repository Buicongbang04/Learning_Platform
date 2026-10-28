# Hướng dẫn chấm: Consistent hashing và quorum replication

Bài advanced không có một đáp án duy nhất. Dưới đây là hướng làm tham khảo, các quyết định thiết kế
cần cân nhắc và rubric.

## Hướng làm

### HashRing

Cấu trúc dữ liệu: `self._points: list[int]` (đã sắp xếp), `self._owner: dict[int, str]`,
`self._nodes: set[str]`.

```python
def add_node(self, node: str) -> None:
    if node in self._nodes:
        raise ValueError(node)
    self._nodes.add(node)
    for i in range(self.vnodes):
        h = stable_hash(f"{node}#{i}")
        if h in self._owner:          # va chạm 64-bit gần như không xảy ra, nhưng xử lý cho chắc
            continue
        self._owner[h] = node
        bisect.insort(self._points, h)

def _start(self, key: str) -> int:
    if not self._points:
        raise LookupError("vòng rỗng")
    return bisect.bisect_left(self._points, stable_hash(key)) % len(self._points)

def get_node(self, key: str) -> str:
    return self._owner[self._points[self._start(key)]]

def get_nodes(self, key: str, n: int) -> list[str]:
    if n > len(self._nodes):
        raise ValueError(...)
    start, out = self._start(key), []
    for i in range(len(self._points)):
        node = self._owner[self._points[(start + i) % len(self._points)]]
        if node not in out:
            out.append(node)
            if len(out) == n:
                break
    return out
```

`remove_node` lọc lại `_points` và `_owner` (O(V), chấp nhận được vì hiếm khi gọi).

### QuorumStore

```python
def _live(self, key):
    return [x for x in self.ring.get_nodes(key, self.n) if x not in self.down]

def put(self, key, value):
    live = self._live(key)
    if len(live) < self.w:
        raise QuorumError(...)                       # kiểm tra TRƯỚC khi ghi
    version = 1 + max((self.data[x].get(key, (0, None))[0] for x in live), default=0)
    for x in live:
        self.data[x][key] = (version, value)
    return version

def get(self, key):
    live = self._live(key)
    if len(live) < self.r:
        raise QuorumError(...)
    asked = live[: self.r]
    found = [self.data[x][key] for x in asked if key in self.data[x]]
    if not found:
        return None
    latest = max(found, key=lambda t: t[0])
    for x in asked:                                   # read repair
        if self.data[x].get(key, (0, None))[0] < latest[0]:
            self.data[x][key] = latest
    return latest[1]
```

### Số đo tham khảo (4 node, 20.000 key, thêm node thứ 5)

| Cách chia | Tỉ lệ key di chuyển | Lý thuyết |
| --- | --- | --- |
| `stable_hash(k) % N` | ~80% | `1 - 1/5` |
| Consistent hashing, 100 vnode | ~21% | `1/5` |

Ảnh hưởng của số vnode tới độ cân bằng (tỉ lệ key của 4 node):

| vnodes | Phân bố |
| --- | --- |
| 1 | 0.7% – 45.5% (rất lệch) |
| 10 | 17% – 41% |
| 100 | 24% – 26% |
| 500 | 24% – 28% |

## Quyết định thiết kế cần cân nhắc

- **Hàm băm**: `hash()` của Python bị ngẫu nhiên hoá theo tiến trình (`PYTHONHASHSEED`), không dùng
  được cho phân tán. Hệ thật dùng Murmur3 (Cassandra) hoặc MD5 (Dynamo ban đầu); quan trọng là ổn
  định và phân bố đều, không cần an toàn mật mã.
- **Số vnode**: nhiều vnode cân bằng hơn và khi một node chết, tải của nó rải đều ra nhiều node thay
  vì dồn vào một láng giềng; đổi lại metadata lớn hơn và streaming khi rebalance phức tạp hơn.
  Cassandra từng mặc định 256, bản mới khuyến nghị 16 kèm thuật toán cấp token thông minh.
- **Node có cấu hình khác nhau**: cho node mạnh nhiều vnode hơn (trọng số).
- **Version**: bài dùng số nguyên tăng dần, đọc-trước-ghi trên replica sống. Hệ thật dùng timestamp
  (Cassandra, last-write-wins, phụ thuộc đồng hồ) hoặc vector clock (Dynamo, phát hiện ghi đồng
  thời để ứng dụng tự gộp). Nên nêu được rằng hai client ghi đồng thời có thể sinh cùng version.
- **Sloppy quorum và hinted handoff**: Dynamo cho phép ghi tạm vào node *không* phải replica khi
  replica chết, rồi chuyển lại sau. Tăng availability nhưng làm `R + W > N` không còn đảm bảo đọc
  mới nhất.
- **Anti-entropy**: read repair chỉ sửa key được đọc; key ít đọc cần quá trình nền so Merkle tree.

## Rubric (100 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Toàn bộ test pass | 35 |
| `get_node` dùng tìm kiếm nhị phân (`bisect`), không quét tuyến tính; `get_nodes` đúng khi vnode của cùng node đứng liền nhau | 10 |
| `put` kiểm tra quorum trước khi ghi, thất bại không để lại dữ liệu; read repair chỉ ghi khi replica cũ hơn | 10 |
| Có số đo di chuyển key so với `hash % N` và ảnh hưởng của số vnode, giải thích đúng (≈ `1/(N+1)` so với ≈ `N/(N+1)`) | 15 |
| Giải thích vì sao `R + W > N` giao nhau, và tình huống quorum vẫn đọc cũ (ghi đồng thời, sloppy quorum, ghi thất bại một phần) | 15 |
| Chất lượng code: type hints, docstring, xử lý lỗi rõ ràng, không lặp code giữa `put`/`get` | 10 |
| Mở rộng (một trong): trọng số vnode, vector clock, hinted handoff, đo phân bố tải khi một node chết | 5 |

Mức đạt: ≥ 70 điểm và toàn bộ test pass.
