-- Metric layer tối giản bằng view trên DuckDB.
-- Bảng nguồn: customers, orders, order_items (xem tests/fixtures/olist_small.sql).
-- Mỗi view đã có đúng tên cột nhưng chưa có logic (WHERE FALSE). Thay phần thân bằng SQL đúng.

-- TODO 1: fct_order_items, grain = một dòng order_items.
-- Cột: order_id, order_date (DATE của order_purchase_timestamp), customer_state, order_status,
--      product_id, price, freight_value.
-- Bỏ đơn có order_status 'canceled' hoặc 'unavailable'.
CREATE OR REPLACE VIEW fct_order_items AS
SELECT
    NULL::VARCHAR AS order_id,
    NULL::DATE    AS order_date,
    NULL::VARCHAR AS customer_state,
    NULL::VARCHAR AS order_status,
    NULL::VARCHAR AS product_id,
    NULL::DOUBLE  AS price,
    NULL::DOUBLE  AS freight_value
WHERE FALSE;

-- TODO 2: metric_daily_revenue, grain = order_date. Dựng trên fct_order_items.
-- orders = số đơn khác nhau, revenue = tổng price, aov = ROUND(revenue / orders, 2).
CREATE OR REPLACE VIEW metric_daily_revenue AS
SELECT
    NULL::DATE   AS order_date,
    NULL::BIGINT AS orders,
    NULL::DOUBLE AS revenue,
    NULL::DOUBLE AS aov
WHERE FALSE;

-- TODO 3: metric_state_summary, grain = customer_state. Dựng trên fct_order_items.
-- orders, revenue, aov như trên; revenue_share = ROUND(revenue / tổng revenue mọi state, 4).
CREATE OR REPLACE VIEW metric_state_summary AS
SELECT
    NULL::VARCHAR AS customer_state,
    NULL::BIGINT  AS orders,
    NULL::DOUBLE  AS revenue,
    NULL::DOUBLE  AS aov,
    NULL::DOUBLE  AS revenue_share
WHERE FALSE;

-- TODO 4: metric_late_rate_by_state, grain = customer_state, chỉ đơn 'delivered'.
-- delivered_orders, late_orders (order_delivered_customer_date > order_estimated_delivery_date),
-- late_rate = ROUND(late_orders / delivered_orders, 4).
-- Cẩn thận fan-out: metric này ở grain đơn hàng, không cần order_items.
CREATE OR REPLACE VIEW metric_late_rate_by_state AS
SELECT
    NULL::VARCHAR AS customer_state,
    NULL::BIGINT  AS delivered_orders,
    NULL::BIGINT  AS late_orders,
    NULL::DOUBLE  AS late_rate
WHERE FALSE;
