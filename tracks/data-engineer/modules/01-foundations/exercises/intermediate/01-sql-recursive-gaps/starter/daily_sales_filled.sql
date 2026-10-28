-- Doanh số mỗi ngày từ ngày nhỏ nhất tới lớn nhất, ngày không có giao dịch ghi 0.
-- Cột: sale_date, amount
-- TODO: sinh date spine rồi LEFT JOIN với tổng theo ngày
SELECT sale_date, SUM(amount) AS amount
FROM daily_sales
GROUP BY sale_date
ORDER BY sale_date
