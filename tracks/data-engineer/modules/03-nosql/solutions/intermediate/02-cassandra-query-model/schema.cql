-- Q1: lịch sử sự kiện của một đơn, mới nhất trước
CREATE TABLE IF NOT EXISTS order_events_by_order (
    order_id    text,
    event_time  timestamp,
    event_type  text,
    location    text,
    PRIMARY KEY ((order_id), event_time, event_type)
) WITH CLUSTERING ORDER BY (event_time DESC, event_type ASC);

-- Q2: các đơn của một seller trong một ngày, mới nhất trước
CREATE TABLE IF NOT EXISTS orders_by_seller_day (
    seller_id    text,
    order_date   date,
    purchased_at timestamp,
    order_id     text,
    order_value  decimal,
    PRIMARY KEY ((seller_id, order_date), purchased_at, order_id)
) WITH CLUSTERING ORDER BY (purchased_at DESC, order_id ASC);

-- Q3: review mới nhất của một sản phẩm
CREATE TABLE IF NOT EXISTS reviews_by_product (
    product_id  text,
    created_at  timestamp,
    review_id   text,
    score       int,
    comment     text,
    PRIMARY KEY ((product_id), created_at, review_id)
) WITH CLUSTERING ORDER BY (created_at DESC, review_id ASC);
