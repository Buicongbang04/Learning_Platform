-- Model mẫu đã làm sẵn: đọc source, đổi tên/chuẩn hoá cột.
select
    customer_id,
    customer_unique_id,
    lower(trim(customer_city)) as customer_city,
    upper(trim(customer_state)) as customer_state
from {{ source('olist', 'customers') }}
