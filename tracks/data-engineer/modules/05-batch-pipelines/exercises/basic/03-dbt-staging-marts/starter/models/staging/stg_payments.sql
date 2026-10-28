-- TODO: từ source('olist', 'payments'):
-- Cột ra: order_id, payment_sequential (integer), payment_type, payment_value (double)
select *
from {{ source('olist', 'payments') }}
