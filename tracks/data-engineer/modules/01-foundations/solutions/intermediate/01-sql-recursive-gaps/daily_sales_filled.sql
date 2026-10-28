-- Doanh số mỗi ngày từ ngày nhỏ nhất tới lớn nhất, ngày không có giao dịch ghi 0.
WITH RECURSIVE days(sale_date) AS (
    SELECT MIN(sale_date) FROM daily_sales
    UNION ALL
    SELECT CAST(sale_date + INTERVAL 1 DAY AS DATE)
    FROM days
    WHERE sale_date < (SELECT MAX(sale_date) FROM daily_sales)
),
daily AS (
    SELECT sale_date, SUM(amount) AS amount
    FROM daily_sales
    GROUP BY sale_date
)
SELECT d.sale_date, COALESCE(s.amount, 0) AS amount
FROM days d
LEFT JOIN daily s USING (sale_date)
ORDER BY d.sale_date
