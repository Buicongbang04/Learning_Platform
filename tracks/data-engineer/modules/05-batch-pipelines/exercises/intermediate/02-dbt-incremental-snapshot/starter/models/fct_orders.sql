-- TODO: biến model này thành incremental:
--   * config(materialized='incremental', unique_key='order_id')
--   * khi is_incremental(): chỉ lấy dòng có updated_at > max(updated_at) đang có trong {{ this }}
-- Cột ra: order_id, customer_id, order_status, amount (double), updated_at (timestamp)
{{ config(materialized='table') }}

select
    order_id,
    customer_id,
    order_status,
    cast(amount as double)        as amount,
    cast(updated_at as timestamp) as updated_at
from {{ source('olist', 'orders') }}
