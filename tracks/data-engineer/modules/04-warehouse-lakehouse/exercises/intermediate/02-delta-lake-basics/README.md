---
title: Delta Lake căn bản - ACID, MERGE, time travel, schema enforcement
level: intermediate
services: []
files:
  - path: starter/delta_ops.py
    note: 7 TODO
  - path: tests/test_delta_ops.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/04-warehouse-lakehouse/exercises/intermediate/02-delta-lake-basics -q
---

## Mục tiêu

Dùng thư viện `deltalake` (delta-rs, không cần Spark) để thấy tận tay những gì table format thêm vào trên
Parquet: transaction log, upsert bằng `MERGE`, đọc lại phiên bản cũ, chặn ghi sai schema và tiến hoá schema có kiểm soát.

## Đề bài

Bảng Delta `orders` có cột `order_id` (string), `order_status` (string), `order_value` (double),
`updated_at` (timestamp). Hoàn thiện `starter/delta_ops.py`:

1. `create_table(path, data) -> int`: tạo bảng mới từ `pyarrow.Table` (lỗi nếu bảng đã tồn tại). Trả version.
2. `append(path, data) -> int`: nối thêm dữ liệu. Trả version mới. Sai schema phải **ném lỗi**, không tự sửa.
3. `upsert(path, updates, key="order_id") -> dict`: `MERGE` theo `key`: trùng khoá thì cập nhật toàn bộ cột,
   chưa có thì chèn. Trả dict metrics mà delta-rs trả về.
4. `read_version(path, version) -> pyarrow.Table`: đọc bảng tại một version (time travel), sắp theo `order_id`.
5. `history_operations(path) -> list[str]`: tên các operation trong history, **cũ nhất trước**
   (vd. `["CREATE TABLE", "WRITE", "MERGE"]`; tên chính xác do delta-rs đặt).
6. `delete_canceled(path) -> int`: xoá các đơn `order_status = 'canceled'`, trả số dòng đã xoá.
7. `append_with_new_column(path, data) -> int`: nối dữ liệu có thêm cột mới (vd. `customer_state`),
   cho phép tiến hoá schema (dòng cũ có giá trị NULL ở cột mới). Trả version mới.

## Tiêu chí đạt

- Version tăng đúng sau mỗi lần ghi (0, 1, 2, ...).
- `upsert` cập nhật đúng dòng trùng khoá và chèn dòng mới, không tạo bản trùng.
- `read_version(path, 0)` trả lại đúng dữ liệu ban đầu sau khi đã sửa nhiều lần.
- `append` với schema sai ném exception; `append_with_new_column` thành công và bảng có cột mới.
- `history_operations` phản ánh đúng thứ tự thao tác.

## Gợi ý

### Gợi ý 1

```python
from deltalake import DeltaTable, write_deltalake
write_deltalake(path, data, mode="error")      # tạo mới
write_deltalake(path, data, mode="append")
DeltaTable(path).version()
DeltaTable(path, version=0).to_pyarrow_table()
```

### Gợi ý 2

```python
(DeltaTable(path)
   .merge(updates, predicate="t.order_id = s.order_id", source_alias="s", target_alias="t")
   .when_matched_update_all()
   .when_not_matched_insert_all()
   .execute())
```

`DeltaTable.history()` trả list dict, **mới nhất trước**, khoá `operation`. `DeltaTable.delete(predicate)` trả metrics có
`num_deleted_rows`. Tiến hoá schema: `write_deltalake(..., mode="append", schema_mode="merge")`.
