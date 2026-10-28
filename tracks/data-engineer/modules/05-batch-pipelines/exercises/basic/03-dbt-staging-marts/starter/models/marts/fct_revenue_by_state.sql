-- TODO: doanh thu theo bang (customer_state) của các đơn delivered.
--   Dùng ref('stg_orders'), ref('stg_customers'), ref('stg_payments').
--   Cột ra: customer_state, orders (số đơn khác nhau), revenue (tổng payment_value)
--   Cẩn thận: một đơn có nhiều payment -> join làm nhân dòng.
select
    cast(null as varchar) as customer_state,
    0 as orders,
    0.0 as revenue
where false
