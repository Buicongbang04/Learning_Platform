-- Cohort retention dạng long: mỗi cohort (tháng mua đầu) × mỗi tháng k quan sát được một dòng.
WITH valid AS (
    SELECT customer_id,
           date_trunc('month', invoice_date)::DATE AS month,
           invoice_date::DATE AS d
    FROM online_retail
    WHERE invoice NOT LIKE 'C%' AND quantity > 0 AND price > 0
      AND customer_id IS NOT NULL                       -- khách vãng lai không theo dõi được
),
last_complete AS (       -- tháng đủ cuối cùng: tháng của ngày cuối nếu ngày đó là cuối tháng, không thì tháng trước
    SELECT CASE WHEN max(d) = last_day(max(d)) THEN date_trunc('month', max(d))::DATE
                ELSE (date_trunc('month', max(d)) - INTERVAL 1 MONTH)::DATE END AS m
    FROM valid
),
first_month AS (         -- cohort = tháng của lần mua hợp lệ đầu tiên
    SELECT customer_id, min(month) AS cohort_month
    FROM valid
    GROUP BY 1
),
sizes AS (
    SELECT cohort_month, count(*) AS cohort_size
    FROM first_month, last_complete lc
    WHERE cohort_month <= lc.m
    GROUP BY 1
),
activity AS (            -- DISTINCT: một khách mua 5 lần trong tháng vẫn là 1 khách active
    SELECT DISTINCT v.customer_id, f.cohort_month,
           date_diff('month', f.cohort_month, v.month) AS month_number
    FROM valid v
    JOIN first_month f USING (customer_id)
    CROSS JOIN last_complete lc
    WHERE v.month <= lc.m
),
counts AS (
    SELECT cohort_month, month_number, count(*) AS active_customers
    FROM activity
    GROUP BY 1, 2
),
grid AS (                -- mọi ô (cohort, k) quan sát được, để ô không ai quay lại vẫn có dòng 0
    SELECT s.cohort_month, s.cohort_size, k AS month_number
    FROM sizes s
    CROSS JOIN last_complete lc
    CROSS JOIN generate_series(0, date_diff('month', s.cohort_month, lc.m)) AS t(k)
)
SELECT g.cohort_month, g.month_number, g.cohort_size,
       coalesce(c.active_customers, 0) AS active_customers,
       round(coalesce(c.active_customers, 0) / g.cohort_size, 4) AS retention
FROM grid g
LEFT JOIN counts c USING (cohort_month, month_number)
ORDER BY g.cohort_month, g.month_number
