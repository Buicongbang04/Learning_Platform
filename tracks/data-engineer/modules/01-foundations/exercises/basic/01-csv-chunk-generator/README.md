---
title: Đọc CSV lớn theo lô bằng generator
level: basic
services: []
files:
  - path: starter/stream.py
    note: 4 TODO
  - path: tests/test_stream.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/01-foundations/exercises/basic/01-csv-chunk-generator -q
---

## Mục tiêu

Viết pipeline đọc file `order_items` kiểu Olist từng dòng bằng generator, gom thành lô và tổng hợp
doanh thu theo seller mà bộ nhớ không phụ thuộc kích thước file. Bỏ qua dòng hỏng thay vì làm sập
cả job.

## Đề bài

File CSV có header `order_id,order_item_id,product_id,seller_id,price,freight_value`. Hoàn thành
4 hàm trong `starter/stream.py`:

1. `read_rows(path)`: **generator** trả từng dòng dạng `dict[str, str]` (dùng `csv.DictReader`,
   mở file bằng `with` bên trong generator, `encoding="utf-8"`, `newline=""`).
2. `batched(iterable, size)`: generator trả các `list` có tối đa `size` phần tử, lô cuối có thể
   ngắn hơn. `size < 1` thì raise `ValueError`. Phải chạy được với iterator vô hạn
   (không được gọi `list(iterable)`).
3. `parse_item(row)`: trả `(seller_id, price + freight_value)` với tiền là `Decimal`. Raise
   `ValueError` nếu `seller_id` rỗng, giá trị không phải số, hoặc `price`/`freight_value` âm.
4. `revenue_by_seller(path, batch_size=1000)`: đọc bằng `read_rows`, xử lý theo lô bằng `batched`,
   trả `dict` gồm:
   - `"rows"`: tổng số dòng dữ liệu đã đọc (không tính header),
   - `"bad_rows"`: số dòng bị `parse_item` từ chối,
   - `"batches"`: số lô đã xử lý,
   - `"revenue"`: `dict[seller_id, Decimal]` tổng `price + freight_value`.

## Tiêu chí đạt

- `read_rows` và `batched` là generator (lazy), `batched` chạy được trên `itertools.count()`.
- `batched` ra đúng lô, lô cuối ngắn hơn, `size=0` raise `ValueError`.
- `parse_item` dùng `Decimal`, từ chối dòng rỗng/không phải số/âm.
- `revenue_by_seller` đếm đúng dòng, dòng lỗi, số lô và tổng tiền trên dữ liệu test.

## Gợi ý

### Gợi ý 1

`yield from csv.DictReader(f)` bên trong khối `with open(...) as f:` là đủ cho `read_rows`.
Với `batched`, dùng `itertools.islice(it, size)` để lấy tối đa `size` phần tử từ một iterator.

### Gợi ý 2

```python
it = iter(iterable)
while batch := list(islice(it, size)):
    yield batch
```

`Decimal("abc")` raise `decimal.InvalidOperation` (là lớp con của `ArithmeticError`, không phải
`ValueError`), nên bắt nó rồi raise `ValueError`. Dùng `collections.defaultdict(Decimal)` để cộng dồn.
