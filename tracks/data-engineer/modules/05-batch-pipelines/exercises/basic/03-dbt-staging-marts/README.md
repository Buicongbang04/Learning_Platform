---
title: dbt project đầu tiên - staging và mart doanh thu theo bang
level: basic
services: []
files:
  - path: starter/dbt_project.yml
    note: 1 TODO
  - path: starter/models/staging/_sources.yml
    note: Đã có sẵn
  - path: starter/models/staging/stg_customers.sql
    note: Model mẫu
  - path: starter/models/staging/stg_orders.sql
    note: 1 TODO
  - path: starter/models/staging/stg_payments.sql
    note: 1 TODO
  - path: starter/models/staging/_stg.yml
    note: 3 TODO
  - path: starter/models/marts/fct_revenue_by_state.sql
    note: 1 TODO
  - path: tests/test_dbt_project.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/05-batch-pipelines/exercises/basic/03-dbt-staging-marts -q
---

## Mục tiêu

Làm quen với dbt theo kiểu ELT: khai báo `source`, viết model staging, nối model bằng `ref`,
chọn materialization và gắn data test. Chạy bằng adapter `dbt-duckdb`.

## Đề bài

Test đóng vai bước **EL**: nạp 3 file CSV thô (`tests/fixtures/`) vào schema `raw` của một tệp
DuckDB (mọi cột là chuỗi), rồi chạy `dbt build` trên bản sao thư mục `starter/` (test tự sinh
`profiles.yml`). Dữ liệu thô có lỗi thật: `order_status` viết hoa lẫn khoảng trắng, một đơn bị
trùng, một dòng thiếu `order_id`, một đơn có nhiều payment.

Việc cần làm trong `starter/`:

1. `dbt_project.yml`: model trong `marts/` materialize thành `table` (staging giữ `view`).
2. `models/staging/stg_orders.sql`: từ `source('olist', 'orders')`, bỏ dòng `order_id` null,
   `order_status = lower(trim(...))`, thêm `purchased_at` (timestamp) và `order_date` (date), mỗi
   `order_id` một dòng. Cột ra đúng thứ tự:
   `order_id, customer_id, order_status, purchased_at, order_date`.
3. `models/staging/stg_payments.sql`: ép `payment_sequential` thành integer, `payment_value` thành
   double. Cột ra: `order_id, payment_sequential, payment_type, payment_value`.
4. `models/marts/fct_revenue_by_state.sql`: doanh thu các đơn `delivered` theo `customer_state`,
   cột `customer_state, orders, revenue`. Chỉ dùng `ref(...)`, không viết tên bảng trực tiếp.
5. `models/staging/_stg.yml`: thêm test cho `stg_orders`: `unique` + `not_null` trên `order_id`,
   `accepted_values` trên `order_status` (delivered, shipped, canceled, invoiced, processing),
   `relationships` từ `customer_id` tới `ref('stg_customers')`.

Muốn tự chạy dbt ngoài test: copy `starter/` ra chỗ khác, tạo `profiles.yml` như trong test, nạp
CSV vào `raw` bằng DuckDB, rồi `uv run dbt build --project-dir . --profiles-dir .`.

## Tiêu chí đạt

- `dbt build` thành công, mọi data test pass.
- `stg_orders` có 5 đơn `o1..o5`, status đã chuẩn hoá, đúng thứ tự cột.
- `fct_revenue_by_state` cho `SP: 2 đơn, 150.0` và `RJ: 1 đơn, 50.0`.
- `stg_orders` là view, `fct_revenue_by_state` là table và phụ thuộc 3 model staging qua `ref`.
- Đủ 4 test khai báo trên `stg_orders`.

## Gợi ý

### Gợi ý 1

Dedup trong SQL: `row_number() over (partition by order_id order by order_purchase_timestamp desc)`
rồi lấy `rn = 1`. Hoặc `select distinct` nếu các dòng trùng giống hệt nhau.

### Gợi ý 2

Đơn `o1` có 2 payment (100 + 20). Nếu join `orders` với `payments` rồi `count(*)` thì số đơn sai.
Gộp payment theo `order_id` trong một CTE trước, hoặc dùng `count(distinct order_id)`.
Cú pháp test có tham số ở dbt ≥ 1.10:

```yaml
- accepted_values:
    arguments:
      values: ['delivered', 'shipped']
```
