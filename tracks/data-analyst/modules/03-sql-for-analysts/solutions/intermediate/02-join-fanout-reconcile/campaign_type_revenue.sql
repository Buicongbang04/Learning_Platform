-- Doanh thu của nhóm hộ theo loại campaign đã nhận; mỗi hộ tính một lần trong mỗi loại.
WITH valid AS (
    SELECT household_key, SALES_VALUE
    FROM transaction_data
    WHERE SALES_VALUE > 0 AND QUANTITY > 0
),
hh_revenue AS (          -- gom về grain hộ TRƯỚC khi join
    SELECT household_key, sum(SALES_VALUE) AS revenue
    FROM valid
    GROUP BY 1
),
hh_type AS (             -- grain (hộ, loại campaign): bỏ trùng các campaign cùng loại
    SELECT DISTINCT household_key, DESCRIPTION AS campaign_type
    FROM campaign_table
),
typed AS (
    SELECT t.campaign_type, t.household_key, coalesce(r.revenue, 0) AS revenue
    FROM hh_type t
    LEFT JOIN hh_revenue r USING (household_key)    -- hộ nhận campaign mà không mua vẫn được đếm
    UNION ALL
    SELECT 'None', r.household_key, r.revenue
    FROM hh_revenue r
    WHERE NOT EXISTS (SELECT 1 FROM campaign_table c WHERE c.household_key = r.household_key)
)
SELECT campaign_type,
       count(*) AS households,
       round(sum(revenue), 2) AS revenue,
       round(sum(revenue) / count(*), 2) AS revenue_per_household
FROM typed
GROUP BY 1
ORDER BY 1
