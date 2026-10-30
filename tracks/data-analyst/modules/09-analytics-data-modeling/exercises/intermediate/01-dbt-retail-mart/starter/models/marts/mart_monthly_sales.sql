-- Grain: một tháng (month = ngày đầu tháng). Bảng cho dashboard doanh thu tháng.
-- Cột theo đúng thứ tự:
--   month, revenue (tổng revenue), orders (số hoá đơn khác nhau), active_customers (số khách có mã khác nhau),
--   new_customers (số khách có cohort_month = month, lấy từ dim_customer; 0 nếu không có),
--   aov (revenue / orders của tháng), is_complete_month (ngày cuối tháng <= ngày bán cuối cùng của cả fact)
-- Metric non-additive (khách, AOV) tính lại từ fact, không cộng từ bảng khác.
-- TODO
select
    cast(null as date)    as month,
    cast(null as double)  as revenue,
    cast(null as bigint)  as orders,
    cast(null as bigint)  as active_customers,
    cast(null as bigint)  as new_customers,
    cast(null as double)  as aov,
    cast(null as boolean) as is_complete_month
from {{ ref('fct_sales_line') }}
where false
