-- Bảng tóm tắt dạng wide cho slide: retention tháng 1, 3, 6, 12 của mỗi cohort; NULL = chưa quan sát được.
WITH valid AS (
    SELECT customer_id, date_trunc('month', invoice_date)::DATE AS month, invoice_date::DATE AS d
    FROM online_retail
    WHERE invoice NOT LIKE 'C%' AND quantity > 0 AND price > 0 AND customer_id IS NOT NULL
),
last_complete AS (
    SELECT CASE WHEN max(d) = last_day(max(d)) THEN date_trunc('month', max(d))::DATE
                ELSE (date_trunc('month', max(d)) - INTERVAL 1 MONTH)::DATE END AS m
    FROM valid
),
first_month AS (
    SELECT customer_id, min(month) AS cohort_month FROM valid GROUP BY 1
),
activity AS (
    SELECT DISTINCT v.customer_id, f.cohort_month, date_diff('month', f.cohort_month, v.month) AS k
    FROM valid v JOIN first_month f USING (customer_id)
),
summary AS (             -- FILTER: pivot có điều kiện, một lần quét
    SELECT f.cohort_month,
           count(DISTINCT f.customer_id) AS cohort_size,
           count(DISTINCT a.customer_id) FILTER (WHERE a.k = 1) AS a1,
           count(DISTINCT a.customer_id) FILTER (WHERE a.k = 3) AS a3,
           count(DISTINCT a.customer_id) FILTER (WHERE a.k = 6) AS a6,
           count(DISTINCT a.customer_id) FILTER (WHERE a.k = 12) AS a12
    FROM first_month f
    LEFT JOIN activity a USING (customer_id, cohort_month)
    GROUP BY 1
)
SELECT s.cohort_month, s.cohort_size,
       -- chỉ báo số khi tháng cohort + k đã đủ dữ liệu; chưa tới thì NULL (khác 0: "không ai quay lại")
       CASE WHEN s.cohort_month + INTERVAL 1 MONTH <= lc.m THEN round(a1 / cohort_size, 4) END AS m1,
       CASE WHEN s.cohort_month + INTERVAL 3 MONTH <= lc.m THEN round(a3 / cohort_size, 4) END AS m3,
       CASE WHEN s.cohort_month + INTERVAL 6 MONTH <= lc.m THEN round(a6 / cohort_size, 4) END AS m6,
       CASE WHEN s.cohort_month + INTERVAL 12 MONTH <= lc.m THEN round(a12 / cohort_size, 4) END AS m12
FROM summary s
CROSS JOIN last_complete lc
WHERE s.cohort_month <= lc.m
ORDER BY s.cohort_month
