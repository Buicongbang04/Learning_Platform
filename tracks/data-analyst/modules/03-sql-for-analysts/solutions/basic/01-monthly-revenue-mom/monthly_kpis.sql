-- KPI theo tháng: doanh thu, số đơn, số ngày bán, MoM, YoY, luỹ kế năm, tháng đã đủ dữ liệu chưa.
WITH valid AS (            -- dòng hợp lệ theo định nghĩa chung của track
    SELECT invoice, invoice_date, quantity * price AS revenue
    FROM online_retail
    WHERE invoice NOT LIKE 'C%' AND quantity > 0 AND price > 0
),
bounds AS (
    SELECT date_trunc('month', min(invoice_date))::DATE AS first_month,
           date_trunc('month', max(invoice_date))::DATE AS last_month,
           max(invoice_date)::DATE AS last_date
    FROM valid
),
spine AS (                 -- mọi tháng từ đầu tới cuối, kể cả tháng không bán được gì
    SELECT CAST(m AS DATE) AS month
    FROM bounds, generate_series(first_month, last_month, INTERVAL 1 MONTH) AS t(m)
),
agg AS (
    SELECT date_trunc('month', invoice_date)::DATE AS month,
           sum(revenue) AS revenue,
           count(DISTINCT invoice) AS orders,
           count(DISTINCT invoice_date::DATE) AS active_days
    FROM valid
    GROUP BY 1
),
filled AS (
    SELECT s.month,
           coalesce(a.revenue, 0) AS revenue,
           coalesce(a.orders, 0) AS orders,
           coalesce(a.active_days, 0) AS active_days,
           last_day(s.month) <= b.last_date AS is_complete
    FROM spine s
    CROSS JOIN bounds b
    LEFT JOIN agg a USING (month)
)
SELECT month,
       round(revenue, 2) AS revenue,
       orders,
       active_days,
       -- NULLIF: tháng trước bằng 0 thì MoM không xác định (NULL), không chia cho 0
       round(revenue / NULLIF(lag(revenue) OVER (ORDER BY month), 0) - 1, 4) AS mom_pct,
       -- LAG 12 dòng chỉ đúng vì spine bảo đảm tháng liên tục
       round(revenue / NULLIF(lag(revenue, 12) OVER (ORDER BY month), 0) - 1, 4) AS yoy_pct,
       round(sum(revenue) OVER (PARTITION BY year(month) ORDER BY month), 2) AS ytd_revenue,
       is_complete
FROM filled
ORDER BY month
