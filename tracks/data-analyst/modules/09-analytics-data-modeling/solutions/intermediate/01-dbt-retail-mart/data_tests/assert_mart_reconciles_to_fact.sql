-- Đối soát: tổng doanh thu và số hoá đơn của mart phải bằng fact. Trả về dòng nào là lỗi.
with mart as (
    select sum(revenue) as revenue, sum(orders) as orders from {{ ref('mart_monthly_sales') }}
),
fct as (
    select sum(revenue) as revenue, count(distinct invoice_no) as orders from {{ ref('fct_sales_line') }}
)
select mart.revenue as mart_revenue, fct.revenue as fct_revenue, mart.orders as mart_orders, fct.orders as fct_orders
from mart cross join fct
where abs(mart.revenue - fct.revenue) > 0.01 or mart.orders <> fct.orders
