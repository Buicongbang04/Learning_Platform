-- Grain: một dòng hàng hợp lệ của hoá đơn (line_id). Doanh thu gộp theo "Định nghĩa dùng chung".
select
    line_id,
    invoice_no,
    invoice_date,
    cast(date_trunc('month', invoice_date) as date) as invoice_month,
    customer_id,
    customer_id is null                            as is_guest,
    stock_code,
    country,
    quantity,
    unit_price,
    quantity * unit_price                          as revenue
from {{ ref('stg_sales_lines') }}
where is_valid_sale
