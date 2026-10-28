-- Q1: lịch sử sự kiện của một đơn, mới nhất trước
CREATE TABLE IF NOT EXISTS order_events_by_order (
    order_id    text,
    event_time  timestamp,
    event_type  text,
    location    text
    -- TODO: thêm dấu phẩy sau cột location, rồi PRIMARY KEY (...)
);
-- TODO: thêm WITH CLUSTERING ORDER BY (...) trước dấu ;

-- Q2: các đơn của một seller trong một ngày, mới nhất trước
CREATE TABLE IF NOT EXISTS orders_by_seller_day (
    seller_id    text,
    order_date   date,
    purchased_at timestamp,
    order_id     text,
    order_value  decimal
    -- TODO: PRIMARY KEY với composite partition key
);

-- Q3: review mới nhất của một sản phẩm
CREATE TABLE IF NOT EXISTS reviews_by_product (
    product_id  text,
    created_at  timestamp,
    review_id   text,
    score       int,
    comment     text
    -- TODO: PRIMARY KEY và CLUSTERING ORDER BY
);
