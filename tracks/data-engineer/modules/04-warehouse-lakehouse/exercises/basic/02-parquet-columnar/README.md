---
title: Parquet và lưu trữ dạng cột với PyArrow
level: basic
services: []
files:
  - path: starter/columnar.py
    note: 5 TODO
  - path: tests/test_columnar.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/04-warehouse-lakehouse/exercises/basic/02-parquet-columnar -q
---

## Mục tiêu

Hiểu vì sao warehouse và lakehouse lưu dữ liệu dạng cột: tự đổi CSV sang Parquet, đọc chỉ vài cột
(column pruning), đọc thống kê min/max của từng row group và dùng nó để bỏ qua dữ liệu (predicate pushdown).

## Đề bài

Hoàn thiện 5 hàm trong `starter/columnar.py`. Test tự sinh một tệp CSV `order_items` khoảng 6.000 dòng
(cột `order_id`, `order_item_id`, `product_id`, `seller_id`, `price`, `freight_value`, `shipping_limit_date`).

1. `csv_to_parquet(csv_path, parquet_path, compression="zstd", row_group_size=1000)`: đọc CSV bằng
   `pyarrow.csv`, ghi Parquet với codec và kích thước row group cho trước. Trả về số dòng đã ghi.
2. `read_columns(parquet_path, columns)`: trả `pyarrow.Table` chỉ gồm các cột được yêu cầu, đúng thứ tự.
3. `row_group_stats(parquet_path, column)`: trả list `(min, max)` của cột đó ở từng row group, đọc từ
   metadata của tệp (không đọc dữ liệu).
4. `size_ratio(csv_path, parquet_path)`: tỉ lệ dung lượng `parquet / csv` (float).
5. `read_expensive_items(parquet_path, min_price)`: trả `pyarrow.Table` các dòng có `price >= min_price`,
   dùng tham số `filters` của `pyarrow.parquet.read_table` để lọc ngay lúc đọc.

## Tiêu chí đạt

- Tệp Parquet có đúng số dòng, codec đúng như tham số, số row group = ceil(số dòng / row_group_size).
- `read_columns` trả đúng tập cột, không đọc thừa.
- `row_group_stats` khớp min/max tính trực tiếp trên từng khúc dữ liệu.
- Parquet (zstd) nhỏ hơn CSV ít nhất 2 lần trên dữ liệu test.
- `read_expensive_items` chỉ trả dòng thoả điều kiện.

## Gợi ý

### Gợi ý 1

`pyarrow.csv.read_csv(path)` trả `Table`. Ghi bằng `pyarrow.parquet.write_table(table, path, compression=..., row_group_size=...)`.
Đọc cột: `pq.read_table(path, columns=[...])`.

### Gợi ý 2

Metadata: `pq.ParquetFile(path).metadata`; `metadata.row_group(i).column(j).statistics` có `.min`, `.max`.
Tìm `j` bằng `metadata.schema.names.index(column)` hoặc so `column(j).path_in_schema`.
Lọc lúc đọc: `pq.read_table(path, filters=[("price", ">=", min_price)])`.
