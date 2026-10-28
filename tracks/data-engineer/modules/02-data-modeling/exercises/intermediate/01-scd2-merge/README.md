---
title: SCD type 2 cho dim_customer và tra surrogate key theo thời điểm
level: intermediate
services: []
files:
  - path: starter/scd2.py
    note: 2 TODO
  - path: tests/test_scd2.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/02-data-modeling/exercises/intermediate/01-scd2-merge -q
---

## Mục tiêu

Viết một bước merge SCD type 2 đúng, idempotent, xử lý cả khách mới, khách đổi, khách bị xoá, NULL;
và tra `customer_key` đúng phiên bản theo ngày mua để nạp fact.

## Đề bài

Bảng `dim_customer` và sequence `customer_key_seq` đã được tạo bởi `create_dim_customer(con)`:

```sql
dim_customer (customer_key INTEGER PRIMARY KEY, customer_id VARCHAR NOT NULL,
              city VARCHAR, state VARCHAR,
              valid_from DATE NOT NULL, valid_to DATE NOT NULL, is_current BOOLEAN NOT NULL)
```

Quy ước: khoảng hiệu lực nửa mở `[valid_from, valid_to)`; dòng hiện hành có
`valid_to = 9999-12-31` và `is_current = TRUE`.

1. `apply_scd2(con, snapshot, as_of)`: `snapshot` là danh sách dict `{"customer_id", "city", "state"}`,
   là **toàn bộ** khách đang tồn tại ở nguồn tại ngày `as_of`.
   - Khách mới (chưa có dòng hiện hành): thêm dòng với `valid_from = as_of`.
   - Khách đổi `city` hoặc `state` (kể cả từ/tới NULL): đóng dòng cũ (`valid_to = as_of`,
     `is_current = FALSE`), thêm dòng mới bắt đầu từ `as_of`.
   - Khách không đổi: không làm gì.
   - Khách có dòng hiện hành nhưng **vắng** trong snapshot (bị xoá ở nguồn): đóng dòng hiện hành, không thêm dòng mới.
   - `customer_key` mới lấy từ `nextval('customer_key_seq')`.
   - Trả về dict đếm `{"inserted": số dòng mới, "closed": số dòng bị đóng}`.
   - Chạy lại cùng snapshot, cùng `as_of` không thay đổi gì (trả `{"inserted": 0, "closed": 0}`).
   - Mọi thay đổi trong một transaction.
2. `lookup_customer_key(con, customer_id, at)`: trả `customer_key` của phiên bản có hiệu lực tại
   ngày `at`, hoặc `None` nếu không có.

## Tiêu chí đạt

- Lịch sử đúng sau nhiều lần chạy với các snapshot khác nhau.
- Mỗi `customer_id` có tối đa một dòng `is_current`; các khoảng hiệu lực không chồng lấn.
- Idempotent khi chạy lại.
- `lookup_customer_key` trả đúng phiên bản ở biên (`at == valid_from` thuộc phiên bản mới, `at == valid_to` thì không thuộc phiên bản cũ).

## Gợi ý

### Gợi ý 1

Nạp snapshot vào bảng tạm `stg`. Thứ tự: (1) đóng dòng hiện hành của khách đổi hoặc bị xoá,
(2) chèn dòng mới cho mọi khách trong `stg` không còn dòng hiện hành. Bước 2 tự bao cả khách mới lẫn khách vừa bị đóng.

### Gợi ý 2

Phát hiện thay đổi NULL-safe: `d.city IS DISTINCT FROM s.city OR d.state IS DISTINCT FROM s.state`.
Khách bị xoá: `NOT EXISTS (SELECT 1 FROM stg s WHERE s.customer_id = d.customer_id)`.
Đếm số dòng bị ảnh hưởng bằng cách đếm trước (`SELECT COUNT(*) ... WHERE <cùng điều kiện>`), hoặc
dùng `UPDATE ... RETURNING customer_key`.
