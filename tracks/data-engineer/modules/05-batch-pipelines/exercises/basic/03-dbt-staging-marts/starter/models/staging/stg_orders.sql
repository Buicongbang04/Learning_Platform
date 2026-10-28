-- TODO: từ source('olist', 'orders'):
--   * bỏ dòng order_id null
--   * order_status = lower(trim(order_status))
--   * purchased_at = cast(order_purchase_timestamp as timestamp)
--   * order_date   = cast(order_purchase_timestamp as date)
--   * mỗi order_id chỉ một dòng
-- Cột ra: order_id, customer_id, order_status, purchased_at, order_date
select *
from {{ source('olist', 'orders') }}
