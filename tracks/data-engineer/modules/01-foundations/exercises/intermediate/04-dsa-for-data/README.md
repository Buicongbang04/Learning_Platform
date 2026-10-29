---
title: DSA cho Data Engineer - partitioning, external sort, top-k, Bloom filter, HyperLogLog
level: intermediate
services: []
files:
  - path: starter/dsa.py
    note: 11 TODO
  - path: tests/test_dsa_for_data.py
    note: Không sửa, dữ liệu sinh trong test với seed cố định
run:
  - uv run pytest tracks/data-engineer/modules/01-foundations/exercises/intermediate/04-dsa-for-data -q
---

## Mục tiêu

Tự cài bằng Python thuần năm cấu trúc dữ liệu và thuật toán nằm bên dưới các công cụ bạn dùng hằng
ngày: hash partitioning (Kafka, Spark shuffle), external merge sort (sort/merge join khi dữ liệu lớn
hơn RAM), top-k bằng heap, Bloom filter (khử trùng lặp, bỏ qua file khi đọc Parquet/Cassandra) và
HyperLogLog (`approx_count_distinct`, `PFCOUNT`). Làm xong bạn hiểu chúng đánh đổi bộ nhớ lấy độ chính
xác thế nào và tính được tham số cho một bài toán cụ thể.

## Đề bài

Hoàn thành `starter/dsa.py`. Docstring mỗi hàm là đặc tả chính xác (công thức, cách băm), vì test so
từng bit với đặc tả. Hàm `hash64` đã viết sẵn: blake2b 8 byte, ổn định giữa các tiến trình, khác với
`hash()` của Python.

1. **`partition_for(key, n)`**: `hash64(key) % n`; `n < 1` thì `ValueError`. Đây là cách Kafka chọn
   partition cho message có key (Kafka dùng murmur2) và cách Spark chia dữ liệu khi shuffle.
2. **`external_sort(lines, out_path, *, max_lines, tmp_dir)`**: sắp xếp một stream dòng khi chỉ được giữ
   `max_lines` dòng trong RAM. Ghi các run đã sort xuống `tmp_dir`, k-way merge ra `out_path`, xoá run,
   trả số run. Test bọc input bằng một iterable kiểm tra bạn **đã ghi run xuống đĩa trước khi đọc tiếp**,
   nên gom hết vào list rồi `sorted()` sẽ trượt.
3. **`top_k(rows, k)`**: `k` cặp `(key, value)` lớn nhất từ một generator, heap không quá `k` phần tử.
   Thứ tự: value giảm dần, cùng value thì key tăng dần. Test thay `heapq.heappush`/`heappushpop`/`heapreplace`
   để đo kích thước heap, nên hãy gọi chúng qua module (`heapq.heappush(...)`), đừng dùng `heapq.nlargest`.
4. **`BloomFilter`**: `optimal_params(n, p)`, `expected_fp_rate(m, k, n)`, `positions` (double hashing),
   `add`, `__contains__`. Bit lưu trong `bytearray` có sẵn.
5. **`HyperLogLog`**: `add`, `count` (có linear counting cho cardinality nhỏ), `merge`.

## Tiêu chí đạt

- `partition_for` đúng công thức, 16.000 khoá chia 8 partition lệch không quá 10%.
- `external_sort` ra đúng thứ tự (kể cả dòng trùng, Unicode, input rỗng), tạo đúng `ceil(n / max_lines)`
  run, run nằm trên đĩa trong lúc đọc và bị xoá sau khi merge.
- `top_k` khớp kết quả sort toàn bộ trên 50.000 dòng có nhiều giá trị trùng, heap không vượt `k`.
- `BloomFilter.optimal_params(1000, 0.01) == (9586, 7)`; không có false negative; với `n = 5000`,
  `p = 0.01` tỉ lệ dương tính giả đo trên 20.000 phần tử lạ không quá 2%.
- `HyperLogLog(p=12)` sai số tương đối không quá 4,9% (ba lần sai số chuẩn) ở 500, 20.000 và 200.000
  phần tử; thêm lại phần tử cũ không đổi ước lượng; `merge` ra ước lượng của hợp hai tập.
- `uv run pytest … -q` pass 21 test.

## Gợi ý

### Gợi ý 1

- External sort: `itertools.islice(it, max_lines)` lấy đúng một chunk mà không đọc dư. `heapq.merge(*iterators)`
  làm sẵn k-way merge, chỉ giữ một dòng của mỗi run trong heap. Đọc run bằng generator mở file và
  `yield line.rstrip("\n")`. Đặt việc xoá run trong `finally`.
- Bloom filter: bit `p` nằm ở `bits[p // 8]`, mặt nạ `1 << (p % 8)`.
- HyperLogLog với `p = 12`: index là `x >> 52`, phần còn lại `w = x & ((1 << 52) - 1)`, số bit 0 đứng đầu
  của `w` trong độ dài 52 là `52 - w.bit_length()`.

### Gợi ý 2

Top-k cần min-heap mà đỉnh là phần tử **kém nhất** trong top-k hiện tại. "Kém hơn" là value nhỏ hơn,
hoặc cùng value nhưng key **lớn** hơn. Không đổi dấu được chuỗi, nên bọc key trong một lớp nhỏ có
`__lt__` đảo chiều:

```python
@dataclass(frozen=True)
class ReverseStr:
    s: str
    def __lt__(self, other):
        return self.s > other.s
```

Phần tử heap là `(value, ReverseStr(key), key)`. Khi heap đủ `k`, chỉ `heapreplace` nếu phần tử mới
tốt hơn đỉnh heap. Cuối cùng `sorted(heap, reverse=True)`.
