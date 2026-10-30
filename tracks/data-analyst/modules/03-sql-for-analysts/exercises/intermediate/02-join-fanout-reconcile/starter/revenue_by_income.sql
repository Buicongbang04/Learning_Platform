-- Doanh thu theo INCOME_DESC; hộ không có nhân khẩu học là 'Unknown'.
-- Cột: income_desc, households, revenue, share. Sắp theo revenue giảm dần.
-- Câu dưới chạy được nhưng SAI (làm rơi hộ). TODO: sửa.
SELECT d.INCOME_DESC AS income_desc,
       count(DISTINCT t.household_key) AS households,
       round(sum(t.SALES_VALUE), 2) AS revenue,
       round(sum(t.SALES_VALUE) / sum(sum(t.SALES_VALUE)) OVER (), 4) AS share
FROM transaction_data t
JOIN hh_demographic d ON d.household_key = t.household_key
WHERE t.SALES_VALUE > 0 AND t.QUANTITY > 0
GROUP BY 1
ORDER BY revenue DESC
