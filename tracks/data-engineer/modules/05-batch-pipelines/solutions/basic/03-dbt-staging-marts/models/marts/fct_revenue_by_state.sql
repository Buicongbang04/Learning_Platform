-- Gộp payment về mức đơn trước khi join để tránh nhân dòng (fan-out).
with order_revenue as (
    select order_id, sum(payment_value) as revenue
    from {{ ref('stg_payments') }}
    group by order_id
),

delivered as (
    select order_id, customer_id
    from {{ ref('stg_orders') }}
    where order_status = 'delivered'
)

select
    c.customer_state,
    count(distinct d.order_id)      as orders,
    sum(coalesce(r.revenue, 0))     as revenue
from delivered d
join {{ ref('stg_customers') }} c using (customer_id)
left join order_revenue r using (order_id)
group by c.customer_state
