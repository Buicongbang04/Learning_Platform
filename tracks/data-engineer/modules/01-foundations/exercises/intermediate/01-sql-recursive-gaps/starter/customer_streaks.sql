-- Số tháng lịch liên tiếp dài nhất có đơn hàng của mỗi khách.
-- Cột: customer_id, longest_streak
-- TODO: DISTINCT tháng, đổi sang số nguyên, trừ ROW_NUMBER, đếm theo nhóm, lấy MAX
SELECT customer_id, COUNT(*) AS longest_streak
FROM orders
GROUP BY customer_id
ORDER BY customer_id
