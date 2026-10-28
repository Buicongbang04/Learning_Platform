-- Serving marts cho dashboard vận hành giao hàng Olist.
-- Nguồn: customers, orders, order_items và bảng run_context(as_of DATE) cho biết "hôm nay" của lần build.
-- Thay phần thân mỗi view/bảng bằng logic của bạn, giữ nguyên tên và cột. Có thể thêm mart khác.

-- TODO 1: mart_ops_daily, grain order_date (ngày đặt), chỉ đơn không canceled/unavailable.
CREATE OR REPLACE TABLE mart_ops_daily AS
SELECT
    NULL::DATE   AS order_date,
    NULL::BIGINT AS orders,
    NULL::BIGINT AS delivered_orders,
    NULL::BIGINT AS late_orders,
    NULL::DOUBLE AS late_rate,       -- late_orders / delivered_orders, NULL khi không có đơn delivered
    NULL::DOUBLE AS revenue,
    NULL::TIMESTAMP AS updated_at
WHERE FALSE;

-- TODO 2: mart_overdue_orders, mỗi đơn CHƯA giao, không canceled/unavailable,
-- đã quá order_estimated_delivery_date tính tới run_context.as_of.
CREATE OR REPLACE TABLE mart_overdue_orders AS
SELECT
    NULL::VARCHAR AS order_id,
    NULL::VARCHAR AS customer_state,
    NULL::VARCHAR AS order_status,
    NULL::DATE    AS estimated_delivery_date,
    NULL::BIGINT  AS days_overdue,
    NULL::VARCHAR AS seller_ids      -- các seller của đơn, nối bằng ',' theo thứ tự tăng dần
WHERE FALSE;

-- TODO 3: mart_seller_late_rate, grain seller_id, tính trên các đơn delivered có item của seller.
CREATE OR REPLACE TABLE mart_seller_late_rate AS
SELECT
    NULL::VARCHAR AS seller_id,
    NULL::BIGINT  AS delivered_orders,
    NULL::BIGINT  AS late_orders,
    NULL::DOUBLE  AS late_rate
WHERE FALSE;
