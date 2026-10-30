-- Kiểm đối chiếu (reconcile) trước khi gửi số: mỗi dòng một phép kiểm, expected lấy từ bảng gốc.
WITH valid AS (
    SELECT household_key, SALES_VALUE
    FROM transaction_data
    WHERE SALES_VALUE > 0 AND QUANTITY > 0
),
hh_revenue AS (
    SELECT household_key, sum(SALES_VALUE) AS revenue FROM valid GROUP BY 1
),
by_income AS (
    SELECT coalesce(d.INCOME_DESC, 'Unknown') AS income_desc, count(*) AS households, sum(r.revenue) AS revenue
    FROM hh_revenue r LEFT JOIN hh_demographic d USING (household_key)
    GROUP BY 1
),
checks AS (
    SELECT 1 AS ord, 'income_revenue_total' AS check_name,
           (SELECT sum(SALES_VALUE) FROM valid) AS expected,
           (SELECT sum(revenue) FROM by_income) AS actual
    UNION ALL
    SELECT 2, 'income_households_total',
           (SELECT count(*) FROM hh_revenue),
           (SELECT sum(households) FROM by_income)
    UNION ALL
    SELECT 3, 'campaign_households_total',     -- hộ 'None' + hộ có campaign = mọi hộ có doanh thu
           (SELECT count(*) FROM hh_revenue),
           (SELECT count(*) FROM hh_revenue r
             WHERE NOT EXISTS (SELECT 1 FROM campaign_table c WHERE c.household_key = r.household_key))
         + (SELECT count(DISTINCT c.household_key) FROM campaign_table c
             JOIN hh_revenue r USING (household_key))
    UNION ALL
    SELECT 4, 'naive_join_revenue_total',      -- phải FAIL: join thẳng nhân bản doanh thu
           (SELECT sum(SALES_VALUE) FROM valid),
           (SELECT sum(v.SALES_VALUE) FROM valid v JOIN campaign_table c USING (household_key))
)
SELECT check_name, round(expected, 2) AS expected, round(actual, 2) AS actual,
       abs(expected - actual) < 0.01 AS passed
FROM checks
ORDER BY ord
