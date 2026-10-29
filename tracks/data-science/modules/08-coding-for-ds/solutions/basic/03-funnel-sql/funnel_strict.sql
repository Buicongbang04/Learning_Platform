-- Như funnel.sql, thêm điều kiện thời gian: mỗi mốc không được sớm hơn mốc trước
-- (duyệt >= mua, giao cho hãng vận chuyển >= duyệt, khách nhận >= giao cho hãng).
WITH latest_review AS (
    SELECT order_id, review_score
    FROM order_reviews
    QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY review_answer_timestamp DESC) = 1
),
flags AS (
    SELECT
        o.order_approved_at >= o.order_purchase_timestamp                             AS approved,
        o.order_delivered_carrier_date >= o.order_approved_at                         AS shipped,
        o.order_status = 'delivered'
            AND o.order_delivered_customer_date >= o.order_delivered_carrier_date     AS delivered,
        r.order_id IS NOT NULL                                                        AS reviewed,
        r.review_score >= 4                                                           AS good_review
    FROM orders o
    LEFT JOIN latest_review r USING (order_id)
),
clean AS (
    -- So sánh với NULL cho NULL; COALESCE về FALSE để FILTER không phụ thuộc vào cách NULL lan truyền
    SELECT COALESCE(approved, FALSE) AS approved, COALESCE(shipped, FALSE) AS shipped,
           COALESCE(delivered, FALSE) AS delivered, reviewed, COALESCE(good_review, FALSE) AS good_review
    FROM flags
),
steps AS (
    SELECT 1 AS step, 'purchased' AS step_name, COUNT(*) AS orders FROM clean
    UNION ALL SELECT 2, 'approved',    COUNT(*) FILTER (approved) FROM clean
    UNION ALL SELECT 3, 'shipped',     COUNT(*) FILTER (approved AND shipped) FROM clean
    UNION ALL SELECT 4, 'delivered',   COUNT(*) FILTER (approved AND shipped AND delivered) FROM clean
    UNION ALL SELECT 5, 'reviewed',    COUNT(*) FILTER (approved AND shipped AND delivered AND reviewed) FROM clean
    UNION ALL SELECT 6, 'good_review', COUNT(*) FILTER (approved AND shipped AND delivered AND reviewed AND good_review) FROM clean
)
SELECT
    step,
    step_name,
    orders,
    orders / COALESCE(LAG(orders) OVER (ORDER BY step), orders)::DOUBLE AS pct_of_prev,
    orders / FIRST_VALUE(orders) OVER (ORDER BY step)::DOUBLE           AS pct_of_first
FROM steps
ORDER BY step;
