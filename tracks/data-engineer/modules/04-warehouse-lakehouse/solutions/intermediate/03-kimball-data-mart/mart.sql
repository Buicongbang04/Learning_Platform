-- Star schema cho mart bán hàng. Chạy tuần tự từng câu lệnh.

CREATE OR REPLACE TABLE dim_customer AS
SELECT 0 AS customer_key, 'unknown' AS customer_id, 'unknown' AS customer_city, 'unknown' AS customer_state
UNION ALL
SELECT
    CAST(ROW_NUMBER() OVER (ORDER BY customer_id) AS INTEGER) AS customer_key,
    customer_id,
    customer_city,
    customer_state
FROM stg_customers;

CREATE OR REPLACE TABLE dim_product AS
SELECT 0 AS product_key, 'unknown' AS product_id, 'unknown' AS category
UNION ALL
SELECT
    CAST(ROW_NUMBER() OVER (ORDER BY product_id) AS INTEGER) AS product_key,
    product_id,
    COALESCE(product_category_name, 'unknown') AS category
FROM stg_products;

CREATE OR REPLACE TABLE dim_date AS
WITH bounds AS (
    SELECT
        MIN(order_purchase_timestamp)::DATE AS d0,
        MAX(order_purchase_timestamp)::DATE AS d1
    FROM stg_orders
),
days AS (
    SELECT unnest(generate_series(d0, d1, INTERVAL 1 DAY))::DATE AS full_date FROM bounds
)
SELECT
    CAST(strftime(full_date, '%Y%m%d') AS INTEGER) AS date_key,
    full_date,
    year(full_date)  AS year,
    month(full_date) AS month,
    day(full_date)   AS day,
    isodow(full_date) AS day_of_week,
    isodow(full_date) IN (6, 7) AS is_weekend
FROM days;

CREATE OR REPLACE TABLE fact_order_items AS
SELECT
    i.order_id,
    i.order_item_id,
    COALESCE(dc.customer_key, 0) AS customer_key,
    COALESCE(dp.product_key, 0)  AS product_key,
    CAST(strftime(o.order_purchase_timestamp, '%Y%m%d') AS INTEGER) AS date_key,
    o.order_status,
    i.price,
    i.freight_value,
    i.price + i.freight_value AS total_value
FROM stg_order_items AS i
JOIN stg_orders AS o USING (order_id)
LEFT JOIN dim_customer AS dc ON dc.customer_id = o.customer_id
LEFT JOIN dim_product  AS dp ON dp.product_id  = i.product_id;
