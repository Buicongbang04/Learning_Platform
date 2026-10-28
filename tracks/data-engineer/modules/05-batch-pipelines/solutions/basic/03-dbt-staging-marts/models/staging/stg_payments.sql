select
    order_id,
    cast(payment_sequential as integer) as payment_sequential,
    payment_type,
    cast(payment_value as double)       as payment_value
from {{ source('olist', 'payments') }}
