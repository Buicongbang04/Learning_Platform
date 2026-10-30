-- Dòng hợp lệ luôn có doanh thu dương; có dòng <= 0 là bộ lọc ở fct sai.
select line_id, revenue from {{ ref('fct_sales_line') }} where revenue <= 0
