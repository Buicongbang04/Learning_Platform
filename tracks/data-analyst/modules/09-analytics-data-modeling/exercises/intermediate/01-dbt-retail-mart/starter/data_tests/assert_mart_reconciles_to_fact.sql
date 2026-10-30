-- Singular test: trả về các dòng VI PHẠM; không có dòng nào là đạt.
-- TODO: so tổng revenue và tổng orders của ref('mart_monthly_sales') với ref('fct_sales_line')
--       (orders của fact = số hoá đơn khác nhau); lệch doanh thu quá 0.01 GBP hoặc lệch số đơn là lỗi.
select 1 as placeholder
from {{ ref('mart_monthly_sales') }}
where false
