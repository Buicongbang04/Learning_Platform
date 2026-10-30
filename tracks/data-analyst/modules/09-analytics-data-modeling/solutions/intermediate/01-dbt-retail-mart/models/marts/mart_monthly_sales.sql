-- Grain: một tháng. Metric non-additive (khách, AOV) tính lại từ fact, không cộng từ bảng khác.
with fct as (
    select * from {{ ref('fct_sales_line') }}
),
months as (
    select
        invoice_month                     as month,
        sum(revenue)                      as revenue,
        count(distinct invoice_no)        as orders,
        count(distinct customer_id)       as active_customers
    from fct
    group by invoice_month
),
new_customers as (
    select cohort_month as month, count(*) as new_customers
    from {{ ref('dim_customer') }}
    group by cohort_month
),
coverage as (
    select max(invoice_date) as last_date from fct
)
select
    m.month,
    m.revenue,
    m.orders,
    m.active_customers,
    coalesce(n.new_customers, 0)                                   as new_customers,
    m.revenue / m.orders                                           as aov,
    (m.month + interval 1 month - interval 1 day) <= c.last_date   as is_complete_month
from months m
left join new_customers n using (month)
cross join coverage c
order by m.month
