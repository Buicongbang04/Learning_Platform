SELECT
    o.customer_state,
    strftime(o.order_purchase_timestamp, '%Y-%m') AS order_month,
    SUM(i.price) AS revenue
FROM orders AS o
JOIN order_items AS i USING (order_id)
WHERE o.order_status = 'delivered'
GROUP BY ROLLUP (o.customer_state, strftime(o.order_purchase_timestamp, '%Y-%m'))
ORDER BY customer_state NULLS LAST, order_month NULLS LAST
