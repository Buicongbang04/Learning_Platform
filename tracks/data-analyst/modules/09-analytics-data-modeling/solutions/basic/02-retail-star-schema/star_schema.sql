-- Star schema cho Online Retail II trên DuckDB.
-- Đầu vào: bảng raw_sales_lines (tên cột như tệp xlsx + source_row = số thứ tự dòng trong tệp).
-- Chạy lại nhiều lần trên cùng kết nối được (CREATE OR REPLACE).

-- Dòng hợp lệ theo "Định nghĩa dùng chung": dùng chung cho mọi bảng bên dưới.
CREATE OR REPLACE TEMP VIEW valid_lines AS
SELECT
    source_row,
    CAST("Invoice" AS VARCHAR)      AS invoice_no,
    CAST("StockCode" AS VARCHAR)    AS stock_code,
    CAST("Description" AS VARCHAR)  AS description,
    "Quantity"                      AS quantity,
    "Price"                         AS unit_price,
    CAST("Customer ID" AS BIGINT)   AS customer_id,
    "Country"                       AS country,
    "InvoiceDate"                   AS invoiced_at
FROM raw_sales_lines
WHERE NOT starts_with(CAST("Invoice" AS VARCHAR), 'C') AND "Quantity" > 0 AND "Price" > 0;

-- dim_date (mẫu có sẵn): mỗi ngày một dòng, liên tục từ ngày bán đầu tới ngày bán cuối.
CREATE OR REPLACE TABLE dim_date AS
WITH bounds AS (
    SELECT CAST(min(invoiced_at) AS DATE) AS lo, CAST(max(invoiced_at) AS DATE) AS hi FROM valid_lines
),
days AS (
    SELECT CAST(d AS DATE) AS full_date
    FROM bounds, generate_series(CAST(lo AS TIMESTAMP), CAST(hi AS TIMESTAMP), INTERVAL 1 DAY) AS t(d)
)
SELECT
    CAST(strftime(full_date, '%Y%m%d') AS INTEGER) AS date_key,
    full_date,
    year(full_date)                                AS year,
    month(full_date)                               AS month,
    CAST(date_trunc('month', full_date) AS DATE)   AS month_start,
    isodow(full_date)                              AS day_of_week,
    isodow(full_date) >= 6                         AS is_weekend
FROM days;

-- dim_product: một dòng mỗi stock_code. Tên = mô tả xuất hiện trên nhiều dòng hợp lệ nhất,
-- hoà thì lấy mô tả nhỏ nhất theo thứ tự chữ cái. Mã không bắt đầu bằng 5 chữ số là phí/điều chỉnh.
CREATE OR REPLACE TABLE dim_product AS
WITH counts AS (
    SELECT stock_code, description, count(*) AS n
    FROM valid_lines
    GROUP BY stock_code, description
),
ranked AS (
    SELECT stock_code, description,
           row_number() OVER (PARTITION BY stock_code ORDER BY n DESC, description) AS rk
    FROM counts
)
SELECT
    CAST(row_number() OVER (ORDER BY stock_code) AS INTEGER) AS product_key,
    stock_code,
    description,
    regexp_matches(stock_code, '^[0-9]{5}')                   AS is_merchandise
FROM ranked
WHERE rk = 1;

-- dim_customer: một dòng mỗi khách có mã + một dòng "khách vãng lai" (customer_key = 0).
-- current_country = quốc gia của dòng hợp lệ muộn nhất (SCD type 1: ghi đè, không giữ lịch sử).
CREATE OR REPLACE TABLE dim_customer AS
SELECT 0 AS customer_key, CAST(NULL AS BIGINT) AS customer_id, 'Unknown' AS current_country,
       CAST(NULL AS DATE) AS first_purchase_date
UNION ALL
SELECT
    CAST(row_number() OVER (ORDER BY customer_id) AS INTEGER),
    customer_id,
    arg_max(country, invoiced_at),
    CAST(min(invoiced_at) AS DATE)
FROM valid_lines
WHERE customer_id IS NOT NULL
GROUP BY customer_id;

-- fct_sales_line: grain = một dòng hàng hợp lệ (line_key = source_row).
-- country là quốc gia ghi trên hoá đơn (thuộc giao dịch), không lấy từ dim_customer.
CREATE OR REPLACE TABLE fct_sales_line AS
SELECT
    v.source_row                                             AS line_key,
    v.invoice_no,
    CAST(strftime(v.invoiced_at, '%Y%m%d') AS INTEGER)       AS date_key,
    coalesce(c.customer_key, 0)                              AS customer_key,
    p.product_key,
    v.country,
    v.quantity,
    v.unit_price,
    v.quantity * v.unit_price                                AS revenue
FROM valid_lines v
JOIN dim_product p USING (stock_code)
LEFT JOIN dim_customer c ON c.customer_id = v.customer_id;
