-- Pipeline Olist: raw -> staging -> mart -> reporting
-- Ghi chú: bảng cũ từng đọc FROM legacy.customers_backup, nay đã bỏ

CREATE TABLE staging.orders AS
SELECT order_id, customer_id, order_status, order_purchase_timestamp
FROM raw.orders
WHERE order_status IS NOT NULL;

create or replace view staging.customers as
select customer_id, customer_unique_id, customer_state
from "raw"."customers";

CREATE TABLE IF NOT EXISTS staging.order_items AS
SELECT * FROM read_parquet('s3://lake/raw/order_items/*.parquet');

INSERT INTO mart.fct_orders (order_id, order_year, revenue)
WITH items AS (
    SELECT order_id, SUM(price + freight_value) AS revenue
    FROM staging.order_items
    GROUP BY order_id
), paid AS (SELECT * FROM items WHERE revenue > 0)
SELECT o.order_id, EXTRACT(YEAR FROM o.order_purchase_timestamp) AS order_year, p.revenue
FROM staging.orders AS o
JOIN paid p ON p.order_id = o.order_id;

CREATE TABLE mart.dim_customers AS
SELECT c.customer_id, c.customer_state, COALESCE(x.n_orders, 0) AS n_orders
FROM staging.customers c
LEFT JOIN (SELECT customer_id, COUNT(*) AS n_orders FROM staging.orders GROUP BY 1) x
  ON x.customer_id = c.customer_id;

/* view cho dashboard, FROM nào trong comment này cũng phải bỏ qua: FROM secret.salaries */
CREATE VIEW reporting.revenue_by_state AS
SELECT d.customer_state, SUM(f.revenue) AS revenue
FROM mart.fct_orders f
INNER JOIN mart.dim_customers d ON d.customer_id = f.order_id
GROUP BY d.customer_state;

SELECT * FROM reporting.revenue_by_state ORDER BY revenue DESC;
