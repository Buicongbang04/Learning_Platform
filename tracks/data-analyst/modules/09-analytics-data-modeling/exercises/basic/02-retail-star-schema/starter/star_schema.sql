-- Star schema cho Online Retail II trên DuckDB.
-- Đầu vào: bảng raw_sales_lines (tên cột như tệp xlsx + source_row = số thứ tự dòng trong tệp).
-- Chạy lại nhiều lần trên cùng kết nối được (CREATE OR REPLACE).

-- Dòng hợp lệ theo "Định nghĩa dùng chung" (có sẵn): dùng chung cho mọi bảng bên dưới.
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

-- dim_product: một dòng mỗi stock_code có ít nhất một dòng hợp lệ.
--   product_key   INTEGER, đánh số 1..n theo stock_code tăng dần
--   description   mô tả xuất hiện trên nhiều dòng hợp lệ nhất của mã; hoà thì lấy mô tả nhỏ nhất theo chữ cái
--   is_merchandise  true khi stock_code bắt đầu bằng 5 chữ số (POST, DOT, M, ... là phí/điều chỉnh)
-- TODO: thay câu lệnh dưới (bảng rỗng đúng cột) bằng truy vấn thật
CREATE OR REPLACE TABLE dim_product AS
SELECT CAST(NULL AS INTEGER) AS product_key, CAST(NULL AS VARCHAR) AS stock_code,
       CAST(NULL AS VARCHAR) AS description, CAST(NULL AS BOOLEAN) AS is_merchandise
WHERE false;

-- dim_customer: một dòng mỗi khách có mã + một dòng unknown member cho khách vãng lai:
--   customer_key = 0, customer_id = NULL, current_country = 'Unknown', first_purchase_date = NULL
--   các khách khác: customer_key INTEGER 1..n theo customer_id tăng dần
--   current_country     quốc gia của dòng hợp lệ muộn nhất của khách (SCD type 1)
--   first_purchase_date ngày (DATE) của dòng hợp lệ sớm nhất
-- TODO
CREATE OR REPLACE TABLE dim_customer AS
SELECT CAST(NULL AS INTEGER) AS customer_key, CAST(NULL AS BIGINT) AS customer_id,
       CAST(NULL AS VARCHAR) AS current_country, CAST(NULL AS DATE) AS first_purchase_date
WHERE false;

-- fct_sales_line: grain = một dòng hàng hợp lệ, line_key = source_row.
--   date_key      YYYYMMDD của invoiced_at (khớp dim_date)
--   customer_key  từ dim_customer; khách vãng lai = 0 (không được để NULL, không được bỏ dòng)
--   product_key   từ dim_product
--   country       quốc gia ghi trên dòng (thuộc giao dịch, không lấy từ dim_customer)
--   revenue       quantity * unit_price
-- TODO
CREATE OR REPLACE TABLE fct_sales_line AS
SELECT CAST(NULL AS BIGINT) AS line_key, CAST(NULL AS VARCHAR) AS invoice_no, CAST(NULL AS INTEGER) AS date_key,
       CAST(NULL AS INTEGER) AS customer_key, CAST(NULL AS INTEGER) AS product_key, CAST(NULL AS VARCHAR) AS country,
       CAST(NULL AS BIGINT) AS quantity, CAST(NULL AS DOUBLE) AS unit_price, CAST(NULL AS DOUBLE) AS revenue
WHERE false;
