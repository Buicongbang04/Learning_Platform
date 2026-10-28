-- Q1: '=' trên seller_id, khoảng + ORDER BY trên shipping_limit_date, cần thêm price để covering.
CREATE INDEX idx_items_seller_date ON order_items (seller_id, shipping_limit_date, price);

-- Q2: '=' trên order_status trước, khoảng trên order_purchase_timestamp sau.
CREATE INDEX idx_orders_status_ts ON orders (order_status, order_purchase_timestamp);

-- Q3: tìm đơn của khách, rồi tìm item theo order_id; price trong index để không đọc bảng.
CREATE INDEX idx_orders_customer ON orders (customer_id);
CREATE INDEX idx_items_order ON order_items (order_id, price);
