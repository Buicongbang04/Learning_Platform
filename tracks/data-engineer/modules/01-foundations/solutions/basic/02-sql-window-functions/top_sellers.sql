-- Top 2 seller theo doanh thu (đơn delivered) trong mỗi bang.
WITH seller_revenue AS (
    SELECT s.seller_state, oi.seller_id, SUM(oi.price) AS revenue
    FROM order_items oi
    JOIN orders o USING (order_id)
    JOIN sellers s USING (seller_id)
    WHERE o.order_status = 'delivered'
    GROUP BY s.seller_state, oi.seller_id
), ranked AS (
    SELECT seller_state, seller_id, revenue,
           DENSE_RANK() OVER (PARTITION BY seller_state ORDER BY revenue DESC) AS rnk
    FROM seller_revenue
)
SELECT seller_state, seller_id, revenue, rnk
FROM ranked
WHERE rnk <= 2
ORDER BY seller_state, rnk, seller_id
