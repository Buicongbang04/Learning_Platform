-- mart_customer cho Marketing. Đầu vào:
--   fct_sales_line(line_id, invoice_no, invoiced_at TIMESTAMP, customer_id BIGINT (NULL = khách vãng lai), country, revenue)
--   params(snapshot_date DATE): ngày chốt; chỉ tính giao dịch có invoiced_at < snapshot_date
-- Grain: một dòng mỗi khách có mã có ít nhất một dòng trước ngày chốt. Cột bắt buộc (thêm cột khác tuỳ thiết kế):
--   customer_id, first_purchase_date (DATE), cohort_month (DATE, ngày đầu tháng mua đầu), last_purchase_date (DATE),
--   recency_days (số ngày từ last_purchase_date tới snapshot_date), orders (số hoá đơn khác nhau), revenue, aov,
--   active_months (số tháng khác nhau có mua), main_country (quốc gia có doanh thu lớn nhất của khách; hoà thì
--   tên nhỏ nhất theo chữ cái), is_winback_target (orders >= 2 và recency_days > 90)
-- Chạy lại được trên cùng kết nối (CREATE OR REPLACE).
-- TODO: thay bảng rỗng dưới bằng truy vấn thật
CREATE OR REPLACE TABLE mart_customer AS
SELECT CAST(NULL AS BIGINT) AS customer_id, CAST(NULL AS DATE) AS first_purchase_date,
       CAST(NULL AS DATE) AS cohort_month, CAST(NULL AS DATE) AS last_purchase_date,
       CAST(NULL AS BIGINT) AS recency_days, CAST(NULL AS BIGINT) AS orders, CAST(NULL AS DOUBLE) AS revenue,
       CAST(NULL AS DOUBLE) AS aov, CAST(NULL AS BIGINT) AS active_months, CAST(NULL AS VARCHAR) AS main_country,
       CAST(NULL AS BOOLEAN) AS is_winback_target
WHERE false;
