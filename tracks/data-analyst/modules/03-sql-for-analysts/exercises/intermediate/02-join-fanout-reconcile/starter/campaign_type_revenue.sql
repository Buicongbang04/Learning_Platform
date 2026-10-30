-- Doanh thu nhóm hộ theo loại campaign (TypeA/B/C) và nhóm 'None' (hộ chưa nhận campaign nào).
-- Cột: campaign_type, households, revenue, revenue_per_household. Sắp theo campaign_type.
-- Câu dưới chạy được nhưng SAI (nhân bản doanh thu). TODO: sửa.
SELECT c.DESCRIPTION AS campaign_type,
       count(DISTINCT t.household_key) AS households,
       round(sum(t.SALES_VALUE), 2) AS revenue,
       round(sum(t.SALES_VALUE) / count(DISTINCT t.household_key), 2) AS revenue_per_household
FROM transaction_data t
JOIN campaign_table c ON c.household_key = t.household_key
WHERE t.SALES_VALUE > 0 AND t.QUANTITY > 0
GROUP BY 1
ORDER BY 1
