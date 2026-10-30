-- Grain: một khách có mã (khách vãng lai không có dòng ở đây).
-- Cột: customer_id, first_purchase_date (ngày của dòng hợp lệ sớm nhất), cohort_month (DATE, ngày đầu tháng đó),
--      current_country (quốc gia của dòng hợp lệ muộn nhất, SCD type 1)
-- TODO
select
    customer_id,
    cast(null as date)    as first_purchase_date,
    cast(null as date)    as cohort_month,
    cast(null as varchar) as current_country
from {{ ref('stg_sales_lines') }}
where false
