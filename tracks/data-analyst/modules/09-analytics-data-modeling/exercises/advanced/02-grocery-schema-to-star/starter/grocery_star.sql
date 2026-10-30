-- Star schema cho schema Grocery Sales (7 bảng quan hệ). Đầu vào: raw_sales, raw_products, raw_categories,
-- raw_customers, raw_cities, raw_countries, raw_employees (tên cột như tệp CSV, xem README của bài).
-- Chạy lại được trên cùng kết nối (CREATE OR REPLACE). Các cột dưới đây phải đứng đầu mỗi bảng, đúng thứ tự;
-- thêm cột khác ở cuối nếu thiết kế của bạn cần.
--
-- Quy ước chung:
--   * Mỗi dimension có một dòng unknown member khoá -1 (tên 'Unknown'); fact không bao giờ có khoá ngoại rỗng.
--   * Khoá thay thế được phép bằng khoá tự nhiên (ProductID, CustomerID, EmployeeID) vì nguồn không có lịch sử
--     thay đổi; ghi lý do trong DESIGN.md.
--   * Dimension là bảng PHẲNG (star, không snowflake): tên danh mục nằm trong dim_product, tên thành phố và quốc
--     gia nằm trong dim_customer / dim_employee.

-- dim_date: mẫu có sẵn. Mỗi ngày từ ngày bán đầu tới ngày bán cuối (date_key = YYYYMMDD), cộng unknown member -1
-- cho dòng bán thiếu SalesDate.
CREATE OR REPLACE TABLE dim_date AS
WITH bounds AS (SELECT CAST(min(SalesDate) AS DATE) AS lo, CAST(max(SalesDate) AS DATE) AS hi FROM raw_sales)
SELECT -1 AS date_key, CAST(NULL AS DATE) AS full_date, CAST(NULL AS BIGINT) AS year, CAST(NULL AS BIGINT) AS month,
       CAST(NULL AS BIGINT) AS day_of_week
UNION ALL
SELECT CAST(strftime(d, '%Y%m%d') AS INTEGER), CAST(d AS DATE), year(d), month(d), isodow(d)
FROM bounds, generate_series(CAST(lo AS TIMESTAMP), CAST(hi AS TIMESTAMP), INTERVAL 1 DAY) AS t(d);

-- TODO dim_product(product_key, product_id, product_name, category_name, class, list_price, is_allergic,
--   vitality_days): một dòng mỗi ProductID; category_name lấy từ raw_categories; list_price = products.Price.
CREATE OR REPLACE TABLE dim_product AS
SELECT CAST(NULL AS BIGINT) AS product_key, CAST(NULL AS BIGINT) AS product_id, CAST(NULL AS VARCHAR) AS product_name,
       CAST(NULL AS VARCHAR) AS category_name, CAST(NULL AS VARCHAR) AS class, CAST(NULL AS DOUBLE) AS list_price,
       CAST(NULL AS VARCHAR) AS is_allergic, CAST(NULL AS DOUBLE) AS vitality_days
WHERE false;

-- TODO dim_customer(customer_key, customer_id, customer_name, city_name, country_name): một dòng mỗi CustomerID;
--   customer_name = FirstName MiddleInitial LastName cách nhau một dấu cách, bỏ phần NULL.
CREATE OR REPLACE TABLE dim_customer AS
SELECT CAST(NULL AS BIGINT) AS customer_key, CAST(NULL AS BIGINT) AS customer_id, CAST(NULL AS VARCHAR) AS customer_name,
       CAST(NULL AS VARCHAR) AS city_name, CAST(NULL AS VARCHAR) AS country_name
WHERE false;

-- TODO dim_employee(employee_key, employee_id, employee_name, city_name, hire_date DATE): một dòng mỗi EmployeeID
--   (nhân viên đóng vai "salesperson" trong fact).
CREATE OR REPLACE TABLE dim_employee AS
SELECT CAST(NULL AS BIGINT) AS employee_key, CAST(NULL AS BIGINT) AS employee_id, CAST(NULL AS VARCHAR) AS employee_name,
       CAST(NULL AS VARCHAR) AS city_name, CAST(NULL AS DATE) AS hire_date
WHERE false;

-- TODO fct_sales(sales_id, transaction_number, date_key, customer_key, product_key, salesperson_key, quantity,
--   unit_price, discount, net_amount): grain một dòng mỗi SalesID, không bỏ dòng nào.
--   * Khoá không tìm thấy trong dimension (hoặc SalesDate NULL) → -1.
--   * TotalPrice của nguồn luôn bằng 0: không dùng. unit_price = list_price của sản phẩm;
--     net_amount = quantity * unit_price * (1 - discount). Sản phẩm không có trong raw_products: để NULL, không bịa.
CREATE OR REPLACE TABLE fct_sales AS
SELECT CAST(NULL AS BIGINT) AS sales_id, CAST(NULL AS VARCHAR) AS transaction_number, CAST(NULL AS INTEGER) AS date_key,
       CAST(NULL AS BIGINT) AS customer_key, CAST(NULL AS BIGINT) AS product_key, CAST(NULL AS BIGINT) AS salesperson_key,
       CAST(NULL AS BIGINT) AS quantity, CAST(NULL AS DOUBLE) AS unit_price, CAST(NULL AS DOUBLE) AS discount,
       CAST(NULL AS DOUBLE) AS net_amount
WHERE false;
