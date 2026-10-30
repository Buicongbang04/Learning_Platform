-- Grain: một dòng hàng hợp lệ của hoá đơn (line_id). Doanh thu gộp theo "Định nghĩa dùng chung".
-- Cột: line_id, invoice_no, invoice_date, invoice_month (DATE, ngày đầu tháng), customer_id,
--      is_guest (customer_id rỗng), stock_code, country, quantity, unit_price, revenue (quantity * unit_price)
-- TODO: chỉ giữ dòng is_valid_sale, tính invoice_month, is_guest, revenue
select
    line_id,
    invoice_no,
    invoice_date,
    cast(null as date)    as invoice_month,
    customer_id,
    cast(null as boolean) as is_guest,
    stock_code,
    country,
    quantity,
    unit_price,
    cast(null as double)  as revenue
from {{ ref('stg_sales_lines') }}
where false
