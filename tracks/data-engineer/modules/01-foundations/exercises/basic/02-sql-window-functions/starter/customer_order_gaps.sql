-- Số thứ tự đơn của mỗi khách và số ngày kể từ đơn trước.
-- Cột: customer_id, order_id, order_purchase_timestamp, order_seq, days_since_prev
-- TODO: ROW_NUMBER và LAG theo customer_id, sắp theo thời gian mua
SELECT customer_id, order_id, order_purchase_timestamp, NULL AS order_seq, NULL AS days_since_prev
FROM orders
