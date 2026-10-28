---
title: dbt incremental model và snapshot SCD Type 2
level: intermediate
services: []
files:
  - path: starter/dbt_project.yml
    note: Đã có sẵn
  - path: starter/models/_sources.yml
    note: Đã có sẵn
  - path: starter/models/_models.yml
    note: Đã có sẵn
  - path: starter/models/fct_orders.sql
    note: 2 TODO
  - path: starter/snapshots/customers_snapshot.sql
    note: 3 TODO
  - path: tests/test_incremental_snapshot.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/05-batch-pipelines/exercises/intermediate/02-dbt-incremental-snapshot -q
---

## Mục tiêu

Hiểu hai cơ chế "có trạng thái" của dbt: **incremental model** (chỉ xử lý phần mới, upsert theo
khoá) và **snapshot** (lưu lịch sử thay đổi của dimension theo kiểu SCD Type 2).

## Đề bài

Test chạy `dbt build` **hai lượt** trên DuckDB:

- Lượt 1: `raw.orders` có `o1, o2, o3`; `raw.customers` có `c1` (sao paulo) và `c2`.
- Giữa hai lượt, nguồn thay đổi: `o1` chuyển `delivered` (updated_at mới), thêm `o4`, thêm `o0` có
  `updated_at` **cũ hơn** mốc đã nạp (mô phỏng dòng không bao giờ được incremental nhìn thấy), và
  `c1` chuyển tới `campinas`.
- Lượt 2: `dbt build` lại.

Việc cần làm:

1. `models/fct_orders.sql`: chuyển sang `materialized='incremental'` với `unique_key='order_id'`.
   Trong khối `{% if is_incremental() %}` chỉ lấy dòng có `updated_at` lớn hơn
   `max(updated_at)` của `{{ this }}`.
2. `snapshots/customers_snapshot.sql`: snapshot `customers_snapshot` trong schema `snapshots`,
   `unique_key='customer_id'`, `strategy='timestamp'`, `updated_at='updated_at'`; select
   `customer_id, customer_city, customer_state` và `updated_at` đã ép kiểu timestamp.

`dbt build` chạy cả seed, model, snapshot và test theo đúng thứ tự phụ thuộc.

## Tiêu chí đạt

- Sau lượt 2, `fct_orders` có `o1` (delivered), `o2`, `o3`, `o4`, không trùng `order_id`.
- `o0` **không** có trong `fct_orders` (chứng tỏ model thật sự chạy incremental, không build lại).
- Manifest ghi `materialized = incremental`, `unique_key = order_id`.
- `snapshots.customers_snapshot` có 2 bản cho `c1` (bản cũ có `dbt_valid_to`, bản mới là bản hiện
  hành) và 1 bản cho `c2`.

## Gợi ý

### Gợi ý 1

```sql
{{ config(materialized='incremental', unique_key='order_id') }}
select ...
from {{ source('olist', 'orders') }}
{% if is_incremental() %}
where cast(updated_at as timestamp) > (select max(updated_at) from {{ this }})
{% endif %}
```

### Gợi ý 2

Khối config của snapshot đặt ngay sau `{% snapshot customers_snapshot %}`:
`{{ config(target_schema='snapshots', unique_key='customer_id', strategy='timestamp', updated_at='updated_at') }}`.
Snapshot thêm các cột `dbt_scd_id`, `dbt_updated_at`, `dbt_valid_from`, `dbt_valid_to`.
