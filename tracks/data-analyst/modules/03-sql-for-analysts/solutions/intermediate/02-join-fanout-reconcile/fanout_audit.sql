-- Đo mức nhân bản khi join thẳng giao dịch với campaign_table (một hộ nhận nhiều campaign).
WITH valid AS (
    SELECT household_key, SALES_VALUE
    FROM transaction_data
    WHERE SALES_VALUE > 0 AND QUANTITY > 0
),
naive AS (               -- join "tự nhiên" mà người mới hay viết: mỗi dòng giao dịch × mỗi campaign của hộ
    SELECT v.SALES_VALUE
    FROM valid v
    JOIN campaign_table c USING (household_key)
)
SELECT (SELECT count(*) FROM valid) AS valid_rows,
       (SELECT count(*) FROM naive) AS joined_rows,
       round((SELECT count(*) FROM naive) / (SELECT count(*) FROM valid), 2) AS fanout_factor,
       round((SELECT sum(SALES_VALUE) FROM valid), 2) AS revenue_true,
       round((SELECT sum(SALES_VALUE) FROM naive), 2) AS revenue_naive,
       round((SELECT sum(SALES_VALUE) FROM naive) / (SELECT sum(SALES_VALUE) FROM valid), 2) AS inflation_factor
