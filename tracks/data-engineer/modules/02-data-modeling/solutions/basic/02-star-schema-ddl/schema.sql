CREATE TABLE dim_date (
    date_key    INTEGER PRIMARY KEY,      -- YYYYMMDD: key "thông minh" chấp nhận được vì ngày không đổi
    full_date   DATE NOT NULL UNIQUE,
    year        INTEGER NOT NULL,
    quarter     INTEGER NOT NULL,
    month       INTEGER NOT NULL,
    day         INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,         -- ISO: thứ Hai = 1 ... Chủ nhật = 7
    is_weekend  BOOLEAN NOT NULL
);

INSERT INTO dim_date
SELECT
    year(d) * 10000 + month(d) * 100 + day(d) AS date_key,
    d                                         AS full_date,
    year(d), quarter(d), month(d), day(d),
    isodow(d)                                 AS day_of_week,
    isodow(d) IN (6, 7)                       AS is_weekend
FROM (
    SELECT CAST(ts AS DATE) AS d
    FROM generate_series(TIMESTAMP '2017-01-01', TIMESTAMP '2018-12-31', INTERVAL 1 DAY) AS t(ts)
);

CREATE TABLE dim_customer (
    customer_key INTEGER PRIMARY KEY,     -- surrogate key
    customer_id  VARCHAR NOT NULL,        -- natural key từ hệ thống nguồn
    city         VARCHAR,
    state        VARCHAR
);

CREATE TABLE dim_product (
    product_key   INTEGER PRIMARY KEY,
    product_id    VARCHAR NOT NULL,
    category_name VARCHAR
);

CREATE TABLE dim_seller (
    seller_key INTEGER PRIMARY KEY,
    seller_id  VARCHAR NOT NULL,
    city       VARCHAR,
    state      VARCHAR
);

CREATE TABLE fact_order_items (
    order_id          VARCHAR NOT NULL,   -- degenerate dimension
    order_item_id     INTEGER NOT NULL,
    purchase_date_key INTEGER NOT NULL REFERENCES dim_date (date_key),
    customer_key      INTEGER NOT NULL REFERENCES dim_customer (customer_key),
    product_key       INTEGER NOT NULL REFERENCES dim_product (product_key),
    seller_key        INTEGER NOT NULL REFERENCES dim_seller (seller_key),
    price             DECIMAL(10, 2) NOT NULL,
    freight_value     DECIMAL(10, 2) NOT NULL,
    PRIMARY KEY (order_id, order_item_id)
);
