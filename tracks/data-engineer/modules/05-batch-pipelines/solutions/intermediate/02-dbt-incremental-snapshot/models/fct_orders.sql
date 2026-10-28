{{
    config(
        materialized='incremental',
        unique_key='order_id',
        incremental_strategy='delete+insert'
    )
}}

select
    order_id,
    customer_id,
    order_status,
    cast(amount as double)        as amount,
    cast(updated_at as timestamp) as updated_at
from {{ source('olist', 'orders') }}

{% if is_incremental() %}
-- {{ this }} là bảng fct_orders đang có. Chỉ lấy phần mới hơn mốc lớn nhất đã nạp.
where cast(updated_at as timestamp) > (select coalesce(max(updated_at), timestamp '1900-01-01') from {{ this }})
{% endif %}
