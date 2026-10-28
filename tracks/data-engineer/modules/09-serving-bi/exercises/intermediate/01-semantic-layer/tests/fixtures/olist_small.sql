-- Bộ dữ liệu Olist thu nhỏ cho test. Không sửa.
CREATE TABLE customers (
    customer_id        VARCHAR PRIMARY KEY,
    customer_unique_id VARCHAR,
    customer_state     VARCHAR
);
INSERT INTO customers VALUES
    ('c1', 'u1', 'SP'),
    ('c2', 'u2', 'SP'),
    ('c3', 'u3', 'RJ'),
    ('c4', 'u4', 'MG'),
    ('c5', 'u1', 'SP');

CREATE TABLE orders (
    order_id                      VARCHAR PRIMARY KEY,
    customer_id                   VARCHAR,
    order_status                  VARCHAR,
    order_purchase_timestamp      TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP
);
INSERT INTO orders VALUES
    ('o1', 'c1', 'delivered', '2018-08-01 10:00:00', '2018-08-05 12:00:00', '2018-08-10 00:00:00'),
    ('o2', 'c2', 'delivered', '2018-08-01 15:30:00', '2018-08-12 09:00:00', '2018-08-08 00:00:00'),
    ('o3', 'c3', 'delivered', '2018-08-02 08:00:00', '2018-08-20 18:00:00', '2018-08-15 00:00:00'),
    ('o4', 'c4', 'canceled',  '2018-08-02 11:00:00', NULL,                  '2018-08-20 00:00:00'),
    ('o5', 'c5', 'shipped',   '2018-08-02 23:59:00', NULL,                  '2018-08-25 00:00:00'),
    ('o6', 'c3', 'delivered', '2018-08-03 09:00:00', '2018-08-12 10:00:00', '2018-08-10 00:00:00');

CREATE TABLE order_items (
    order_id      VARCHAR,
    order_item_id INTEGER,
    product_id    VARCHAR,
    seller_id     VARCHAR,
    price         DOUBLE,
    freight_value DOUBLE
);
INSERT INTO order_items VALUES
    ('o1', 1, 'p1', 's1', 100.0, 10.0),
    ('o1', 2, 'p2', 's2',  50.0,  5.0),
    ('o2', 1, 'p1', 's1', 100.0, 12.0),
    ('o3', 1, 'p3', 's2', 200.0, 20.0),
    ('o3', 2, 'p3', 's2', 200.0, 20.0),
    ('o4', 1, 'p2', 's2',  50.0,  5.0),
    ('o5', 1, 'p4', 's3',  30.0,  8.0),
    ('o6', 1, 'p2', 's2',  50.0,  6.0);
