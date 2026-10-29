-- Phễu vòng đời đơn hàng Olist: mỗi đơn chỉ được tính ở bước k nếu đã qua MỌI bước trước đó.
WITH latest_review AS (
    SELECT order_id, review_score
    FROM order_reviews
    QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY review_answer_timestamp DESC) = 1
),
flags AS (
    SELECT
        o.order_approved_at IS NOT NULL                                              AS approved,
        o.order_delivered_carrier_date IS NOT NULL                                   AS shipped,
        o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL AS delivered,
        r.order_id IS NOT NULL                                                       AS reviewed,
        COALESCE(r.review_score >= 4, FALSE)                                         AS good_review
    FROM orders o
    LEFT JOIN latest_review r USING (order_id)
),
steps AS (
    SELECT 1 AS step, 'purchased' AS step_name, COUNT(*) AS orders FROM flags
    UNION ALL SELECT 2, 'approved',    COUNT(*) FILTER (approved) FROM flags
    UNION ALL SELECT 3, 'shipped',     COUNT(*) FILTER (approved AND shipped) FROM flags
    UNION ALL SELECT 4, 'delivered',   COUNT(*) FILTER (approved AND shipped AND delivered) FROM flags
    UNION ALL SELECT 5, 'reviewed',    COUNT(*) FILTER (approved AND shipped AND delivered AND reviewed) FROM flags
    UNION ALL SELECT 6, 'good_review', COUNT(*) FILTER (approved AND shipped AND delivered AND reviewed AND good_review) FROM flags
)
SELECT
    step,
    step_name,
    orders,
    orders / COALESCE(LAG(orders) OVER (ORDER BY step), orders)::DOUBLE AS pct_of_prev,
    orders / FIRST_VALUE(orders) OVER (ORDER BY step)::DOUBLE           AS pct_of_first
FROM steps
ORDER BY step;
