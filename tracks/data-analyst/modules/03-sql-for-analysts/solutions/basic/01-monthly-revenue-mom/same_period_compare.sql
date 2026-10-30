-- So sánh công bằng khi kỳ hiện tại chưa đủ: cùng số ngày ở tháng trước, cùng kỳ năm trước, luỹ kế năm.
WITH valid AS (
    SELECT invoice_date::DATE AS d, quantity * price AS revenue
    FROM online_retail
    WHERE invoice NOT LIKE 'C%' AND quantity > 0 AND price > 0
),
cut AS (                   -- mốc cắt lấy từ dữ liệu, không gõ cứng ngày
    SELECT max(d) AS last_date,
           date_trunc('month', max(d))::DATE AS cur_month,
           date_trunc('year', max(d))::DATE AS cur_year
    FROM valid
),
periods AS (
    -- trừ INTERVAL trên DATE tự kẹp về ngày cuối tháng: 30/03 - 1 tháng = 28/02
    SELECT 'mtd' AS period, cur_month AS start_date, last_date AS end_date, 1 AS ord FROM cut
    UNION ALL
    SELECT 'mtd_prev_month', (cur_month - INTERVAL 1 MONTH)::DATE, (last_date - INTERVAL 1 MONTH)::DATE, 2 FROM cut
    UNION ALL
    SELECT 'mtd_prev_year', (cur_month - INTERVAL 1 YEAR)::DATE, (last_date - INTERVAL 1 YEAR)::DATE, 3 FROM cut
    UNION ALL
    SELECT 'ytd', cur_year, last_date, 4 FROM cut
    UNION ALL
    SELECT 'ytd_prev_year', (cur_year - INTERVAL 1 YEAR)::DATE, (last_date - INTERVAL 1 YEAR)::DATE, 5 FROM cut
)
SELECT p.period, p.start_date, p.end_date, round(coalesce(sum(v.revenue), 0), 2) AS revenue
FROM periods p
LEFT JOIN valid v ON v.d BETWEEN p.start_date AND p.end_date   -- LEFT JOIN: kỳ không bán gì vẫn có dòng 0
GROUP BY p.period, p.start_date, p.end_date, p.ord
ORDER BY p.ord
