WITH monthly AS (
    SELECT
        strftime(o.order_purchase_timestamp, '%Y-%m') AS order_month,
        SUM(i.price) AS revenue
    FROM orders AS o
    JOIN order_items AS i USING (order_id)
    WHERE o.order_status = 'delivered'
    GROUP BY 1
)
SELECT
    order_month,
    revenue,
    SUM(revenue) OVER (ORDER BY order_month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_revenue,
    ROUND((revenue - LAG(revenue) OVER (ORDER BY order_month))
          / LAG(revenue) OVER (ORDER BY order_month) * 100, 2) AS mom_growth_pct
FROM monthly
ORDER BY order_month
