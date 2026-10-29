-- "Đợt hoạt động" của mỗi seller: như streaks.sql nhưng cho phép nghỉ TỐI ĐA 1 tháng ở giữa.
-- Nghỉ từ 2 tháng liên tiếp trở lên thì đợt kết thúc (định nghĩa churn của bài).
-- Kết quả: seller_id, start_month, end_month, active_months (số tháng có bán),
--          span_months (số tháng từ start tới end, tính cả hai đầu); sắp theo seller_id, start_month.
-- TODO: LAG(month) để biết khoảng cách tới tháng hoạt động trước
-- TODO: cờ is_new khi khoảng cách > 2 tháng (hoặc là dòng đầu), SUM(is_new) OVER (...) ra số thứ tự đợt
SELECT NULL::VARCHAR AS seller_id, NULL::DATE AS start_month, NULL::DATE AS end_month,
       NULL::BIGINT AS active_months, NULL::BIGINT AS span_months
WHERE FALSE;
