-- Số tháng lịch liên tiếp dài nhất có đơn hàng của mỗi khách (gaps-and-islands).
WITH months AS (
    SELECT DISTINCT
        customer_id,
        year(order_purchase_timestamp) * 12 + month(order_purchase_timestamp) AS month_idx
    FROM orders
),
islands AS (
    SELECT
        customer_id,
        month_idx - ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY month_idx) AS grp
    FROM months
),
streaks AS (
    SELECT customer_id, grp, COUNT(*) AS streak
    FROM islands
    GROUP BY customer_id, grp
)
SELECT customer_id, MAX(streak) AS longest_streak
FROM streaks
GROUP BY customer_id
ORDER BY customer_id
