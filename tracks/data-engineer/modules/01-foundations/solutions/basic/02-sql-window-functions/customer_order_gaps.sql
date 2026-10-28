-- Số thứ tự đơn của mỗi khách và số ngày kể từ đơn trước.
SELECT
    customer_id,
    order_id,
    order_purchase_timestamp,
    ROW_NUMBER() OVER w AS order_seq,
    date_diff(
        'day',
        CAST(LAG(order_purchase_timestamp) OVER w AS DATE),
        CAST(order_purchase_timestamp AS DATE)
    ) AS days_since_prev
FROM orders
WINDOW w AS (PARTITION BY customer_id ORDER BY order_purchase_timestamp, order_id)
ORDER BY customer_id, order_seq
