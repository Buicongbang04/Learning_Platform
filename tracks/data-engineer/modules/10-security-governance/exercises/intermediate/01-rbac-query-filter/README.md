---
title: RBAC, column masking và row-level security cho truy vấn DuckDB
level: intermediate
services: []
files:
  - path: starter/rbac.py
    note: 3 TODO
  - path: tests/test_rbac.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/10-security-governance/exercises/intermediate/01-rbac-query-filter -q
---

## Mục tiêu

Tự dựng một lớp phân quyền nhỏ đứng trước database: kiểm tra quyền theo role (deny by default), che cột
nhạy cảm (column masking), lọc dòng theo người dùng (row-level security) và sinh SQL **có tham số** để
không bị SQL injection.

## Đề bài

Bảng `order_items` (DuckDB) có các cột trong `TABLE_COLUMNS`. `POLICIES` trong starter đã khai báo quyền:

| Role | Cột được đọc | Cột bị che (`md5`) | Row filter |
| --- | --- | --- | --- |
| `admin` | tất cả | không | không |
| `analyst` | mọi cột trừ `customer_cpf` | `customer_email` | không |
| `seller` | `order_id`, `order_item_id`, `product_id`, `seller_id`, `price`, `freight_value` | không | `seller_id = user["seller_id"]` |

Hoàn thiện `starter/rbac.py`:

1. `allowed_columns(role, table, requested)`:
   - Role hoặc bảng không có trong `POLICIES` → `PermissionError` (deny by default).
   - `requested == ["*"]` → trả toàn bộ cột được phép, **theo thứ tự trong `TABLE_COLUMNS`**.
   - Có cột không được phép (kể cả cột không tồn tại) → `PermissionError`. Ngược lại trả `requested` giữ thứ tự.
2. `build_query(user, table, columns, where=None)` trả `(sql, params)`:
   - `user` là dict có `role` và (với seller) `seller_id`.
   - Mỗi cột thường render `"col"`; cột bị che render `md5("col") AS "col"`.
   - Row filter của policy: thêm `"seller_id" = ?` với giá trị `user["seller_id"]`; seller không có
     `seller_id` → `PermissionError`.
   - `where` là dict `{cột: giá trị}`, mỗi cặp thêm `"cột" = ?`. Cột trong `where` cũng phải là cột được phép
     (không cho lọc theo cột bị cấm để dò dữ liệu) và **không** được là cột bị che.
   - Các điều kiện nối bằng `AND`; giá trị **luôn** đi qua `params`, không bao giờ ghép vào chuỗi SQL.
3. `run_query(con, user, table, columns, where=None)` chạy SQL trên kết nối DuckDB và trả `pandas.DataFrame`.

## Tiêu chí đạt

- Admin đọc được mọi cột; analyst thấy email đã hash, không đọc được CPF; seller chỉ thấy dòng của mình.
- Role lạ, bảng lạ, cột lạ đều bị từ chối.
- Chuỗi kiểu `"' OR 1=1 --"` trong `where` không làm lộ thêm dòng nào.
- Test pass.

## Gợi ý

### Gợi ý 1

Kiểm tra quyền **trước** khi sinh SQL: tên cột chỉ được lấy từ danh sách cho phép, nên không thể chèn
`price; DROP TABLE order_items` vào phần identifier.

### Gợi ý 2

DuckDB nhận tham số `?`: `con.execute(sql, params).df()`. Gom điều kiện vào list rồi
`" WHERE " + " AND ".join(conds)` nếu list không rỗng.
