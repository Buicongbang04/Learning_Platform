with src as (
    select
        order_id,
        customer_id,
        lower(trim(order_status))                   as order_status,
        cast(order_purchase_timestamp as timestamp) as purchased_at,
        cast(order_purchase_timestamp as date)      as order_date,
        row_number() over (
            partition by order_id
            order by order_purchase_timestamp desc
        ) as rn
    from {{ source('olist', 'orders') }}
    where order_id is not null
)
select order_id, customer_id, order_status, purchased_at, order_date
from src
where rn = 1
