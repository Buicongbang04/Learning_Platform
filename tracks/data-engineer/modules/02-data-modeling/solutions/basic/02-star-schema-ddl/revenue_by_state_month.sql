SELECT d.year, d.month, c.state, SUM(f.price) AS revenue
FROM fact_order_items f
JOIN dim_date d     ON d.date_key = f.purchase_date_key
JOIN dim_customer c ON c.customer_key = f.customer_key
GROUP BY d.year, d.month, c.state
ORDER BY d.year, d.month, revenue DESC;
