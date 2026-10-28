-- Lời giải: metric layer bằng view trên DuckDB.

CREATE OR REPLACE VIEW fct_order_items AS
SELECT
    o.order_id,
    CAST(o.order_purchase_timestamp AS DATE) AS order_date,
    c.customer_state,
    o.order_status,
    oi.product_id,
    oi.price,
    oi.freight_value
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN customers c ON c.customer_id = o.customer_id
WHERE o.order_status NOT IN ('canceled', 'unavailable');

CREATE OR REPLACE VIEW metric_daily_revenue AS
SELECT
    order_date,
    COUNT(DISTINCT order_id)                          AS orders,
    SUM(price)                                        AS revenue,
    ROUND(SUM(price) / COUNT(DISTINCT order_id), 2)   AS aov
FROM fct_order_items
GROUP BY order_date;

CREATE OR REPLACE VIEW metric_state_summary AS
WITH by_state AS (
    SELECT
        customer_state,
        COUNT(DISTINCT order_id) AS orders,
        SUM(price)               AS revenue
    FROM fct_order_items
    GROUP BY customer_state
)
SELECT
    customer_state,
    orders,
    revenue,
    ROUND(revenue / orders, 2)                    AS aov,
    ROUND(revenue / SUM(revenue) OVER (), 4)      AS revenue_share
FROM by_state;

CREATE OR REPLACE VIEW metric_late_rate_by_state AS
WITH delivered AS (
    SELECT
        c.customer_state,
        o.order_id,
        o.order_delivered_customer_date > o.order_estimated_delivery_date AS is_late
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
)
SELECT
    customer_state,
    COUNT(*)                                           AS delivered_orders,
    COUNT(*) FILTER (WHERE is_late)                    AS late_orders,
    ROUND(COUNT(*) FILTER (WHERE is_late) / COUNT(*), 4) AS late_rate
FROM delivered
GROUP BY customer_state;
