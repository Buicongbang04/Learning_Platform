---
title: Quality gate cho bảng orders bằng pandera
level: basic
services: []
files:
  - path: starter/quality.py
    note: 3 TODO
  - path: tests/test_quality.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/10-security-governance/exercises/basic/03-data-quality-pandera -q
---

## Mục tiêu

Biến các data quality dimension (completeness, uniqueness, validity, consistency) thành schema pandera
chạy được, rồi dùng nó làm quality gate: tách dòng sạch khỏi dòng lỗi (quarantine) và sinh báo cáo.

## Đề bài

Hoàn thiện `starter/quality.py`:

1. `build_orders_schema()` trả `pa.DataFrameSchema` cho bảng orders kiểu Olist:

   | Cột | Kiểu | Ràng buộc |
   | --- | --- | --- |
   | `order_id` | `str` | không null, unique |
   | `customer_id` | `str` | không null |
   | `order_status` | `str` | thuộc `ORDER_STATUSES` |
   | `order_purchase_timestamp` | `datetime64[ns]`, `coerce=True` | không null |
   | `order_delivered_customer_date` | `datetime64[ns]`, `coerce=True` | được null |
   | `price` | `float` | `> 0` |
   | `freight_value` | `float` | `>= 0` |

   Thêm một check mức DataFrame tên **`delivered_after_purchase`**: nếu
   `order_delivered_customer_date` không null thì phải `>=` `order_purchase_timestamp`.
   Schema để `strict=False` (cho phép cột thừa).
2. `validate(df)` chạy schema với `lazy=True` và trả tuple `(valid_df, failures)`:
   - `failures`: DataFrame có ít nhất các cột `index`, `column`, `check`, `failure_case` (lấy từ
     `SchemaErrors.failure_cases`); rỗng (0 dòng, vẫn có đủ cột) nếu dữ liệu sạch.
   - `valid_df`: các dòng của `df` gốc có index **không** xuất hiện trong `failures["index"]`.
3. `quality_report(df)` trả dict:
   `{"rows": int, "valid_rows": int, "invalid_rows": int, "failed_checks": {check: số dòng lỗi khác nhau}}`.

## Tiêu chí đạt

- Dữ liệu sạch: `failures` rỗng, `valid_df` đủ dòng.
- Bắt được: trùng `order_id`, `order_id` null, status lạ, giá âm, giao hàng trước ngày mua.
- Một dòng vi phạm nhiều check chỉ bị đếm một lần trong `invalid_rows`.
- Test pass.

## Gợi ý

### Gợi ý 1

`import pandera.pandas as pa`. Check mức DataFrame: `pa.Check(lambda d: ..., name="delivered_after_purchase")`
đặt trong tham số `checks=[...]` của `DataFrameSchema`; hàm trả Series bool.

### Gợi ý 2

```python
try:
    schema.validate(df, lazy=True)
except pa.errors.SchemaErrors as err:
    fc = err.failure_cases
```

Dòng `not_nullable` có `index` là số dòng thật; vài lỗi mức schema có `index` là NaN, nên `dropna()`
trước khi đổi sang `int`.
