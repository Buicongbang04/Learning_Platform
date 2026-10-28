---
title: SCD type 1 và type 3 cho dimension seller
level: basic
services: []
files:
  - path: starter/scd.py
    note: 2 TODO
  - path: tests/test_scd.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/02-data-modeling/exercises/basic/03-scd1-scd3 -q
---

## Mục tiêu

Cài đặt hai cách đơn giản nhất để xử lý thuộc tính dimension thay đổi: ghi đè (type 1) và giữ một
bước lịch sử bằng cột `previous_*` (type 3), đều idempotent.

## Đề bài

Hai bảng đã được tạo sẵn bởi hàm `create_tables(con)` trong `starter/scd.py` (DuckDB):

```sql
dim_seller      (seller_id VARCHAR PRIMARY KEY, city VARCHAR, state VARCHAR)
dim_seller_scd3 (seller_id VARCHAR PRIMARY KEY, current_state VARCHAR,
                 previous_state VARCHAR, state_changed_on DATE)
```

Đầu vào `rows` là danh sách dict `{"seller_id", "city", "state"}` (snapshot mới nhất từ nguồn).

1. `apply_scd1(con, rows)`: seller mới thì thêm; seller đã có thì **ghi đè** `city`, `state`.
2. `apply_scd3(con, rows, as_of)`:
   - Seller mới: `current_state = state`, `previous_state = NULL`, `state_changed_on = NULL`.
   - Seller đổi bang: `previous_state` = bang hiện tại cũ, `current_state` = bang mới,
     `state_changed_on = as_of`.
   - Seller không đổi bang: giữ nguyên dòng (kể cả `state_changed_on`).

Seller vắng mặt trong `rows` thì giữ nguyên. Gọi lại cùng `rows` lần nữa không làm thay đổi gì.

## Tiêu chí đạt

- `apply_scd1` thêm seller mới và ghi đè thuộc tính seller cũ; số dòng bằng số seller khác nhau.
- `apply_scd3` lưu đúng bang trước đó và ngày đổi; chạy lại cùng snapshot không đổi kết quả.
- Không dùng vòng lặp `SELECT` từng dòng rồi so sánh trong Python là tốt nhất (không bắt buộc).

## Gợi ý

### Gợi ý 1

Đưa `rows` vào một bảng tạm: `con.execute("CREATE TEMP TABLE stg (seller_id VARCHAR, city VARCHAR, state VARCHAR)")`
rồi `con.executemany("INSERT INTO stg VALUES (?, ?, ?)", ...)`. Sau đó mọi việc là SQL.

### Gợi ý 2

Type 1: `INSERT INTO dim_seller SELECT * FROM stg ON CONFLICT (seller_id) DO UPDATE SET city = excluded.city, state = excluded.state`.
Type 3: một câu `UPDATE ... FROM stg WHERE d.current_state IS DISTINCT FROM s.state` rồi một câu
`INSERT ... WHERE NOT EXISTS (...)`. Chú ý: trong `SET`, vế phải đọc giá trị **cũ** của dòng, nên
`previous_state = current_state, current_state = s.state` là đúng.
