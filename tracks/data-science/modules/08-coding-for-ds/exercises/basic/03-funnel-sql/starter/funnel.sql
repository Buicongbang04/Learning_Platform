-- Phễu vòng đời đơn hàng Olist trên DuckDB. Bảng có sẵn: orders, order_reviews.
-- Kết quả: 6 dòng, cột step, step_name, orders, pct_of_prev, pct_of_first (xem README).
-- TODO: CTE latest_review (mỗi đơn giữ review có review_answer_timestamp mới nhất)
-- TODO: CTE cờ cho từng bước, bước k chỉ tính khi đã qua mọi bước trước
-- TODO: tỉ lệ so với bước trước (LAG) và so với bước đầu (FIRST_VALUE)
SELECT 1 AS step, 'purchased' AS step_name, COUNT(*) AS orders, 1.0 AS pct_of_prev, 1.0 AS pct_of_first
FROM orders;
