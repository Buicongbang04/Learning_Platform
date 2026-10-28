-- Doanh thu theo ngày (đơn delivered) kèm luỹ kế trong tháng và trung bình trượt 3 dòng.
WITH daily AS (
    SELECT CAST(o.order_purchase_timestamp AS DATE) AS order_date, SUM(oi.price) AS revenue
    FROM orders o
    JOIN order_items oi USING (order_id)
    WHERE o.order_status = 'delivered'
    GROUP BY 1
)
SELECT
    order_date,
    revenue,
    SUM(revenue) OVER (
        PARTITION BY date_trunc('month', order_date)
        ORDER BY order_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS mtd_revenue,
    ROUND(AVG(revenue) OVER (ORDER BY order_date ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS ma3
FROM daily
ORDER BY order_date
