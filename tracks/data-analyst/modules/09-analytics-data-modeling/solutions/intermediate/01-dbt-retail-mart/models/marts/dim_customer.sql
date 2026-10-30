-- Grain: một khách có mã. Quốc gia hiện tại = quốc gia của dòng hợp lệ muộn nhất (SCD type 1).
select
    customer_id,
    min(invoice_date)                                                as first_purchase_date,
    cast(date_trunc('month', min(invoice_date)) as date)             as cohort_month,
    arg_max(country, invoiced_at)                                    as current_country
from {{ ref('stg_sales_lines') }}
where is_valid_sale and customer_id is not null
group by customer_id
