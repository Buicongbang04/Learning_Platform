-- Bảng cha trước, bảng con sau (khoá ngoại cần bảng được tham chiếu tồn tại).

CREATE TABLE customers (
    customer_id    VARCHAR PRIMARY KEY,
    customer_city  VARCHAR,
    customer_state VARCHAR
);
INSERT INTO customers
SELECT DISTINCT customer_id, customer_city, customer_state FROM orders_flat;

CREATE TABLE sellers (
    seller_id    VARCHAR PRIMARY KEY,
    seller_city  VARCHAR,
    seller_state VARCHAR
);
INSERT INTO sellers
SELECT DISTINCT seller_id, seller_city, seller_state FROM orders_flat;

CREATE TABLE products (
    product_id            VARCHAR PRIMARY KEY,
    product_category_name VARCHAR
);
INSERT INTO products
SELECT DISTINCT product_id, product_category_name FROM orders_flat;

CREATE TABLE orders (
    order_id                 VARCHAR PRIMARY KEY,
    customer_id              VARCHAR NOT NULL REFERENCES customers (customer_id),
    order_status             VARCHAR,
    order_purchase_timestamp TIMESTAMP
);
INSERT INTO orders
SELECT DISTINCT order_id, customer_id, order_status, order_purchase_timestamp FROM orders_flat;

CREATE TABLE order_items (
    order_id      VARCHAR NOT NULL REFERENCES orders (order_id),
    order_item_id INTEGER NOT NULL,
    product_id    VARCHAR NOT NULL REFERENCES products (product_id),
    seller_id     VARCHAR NOT NULL REFERENCES sellers (seller_id),
    price         DECIMAL(10, 2),
    freight_value DECIMAL(10, 2),
    PRIMARY KEY (order_id, order_item_id)
);
INSERT INTO order_items
SELECT order_id, order_item_id, product_id, seller_id, price, freight_value FROM orders_flat;
