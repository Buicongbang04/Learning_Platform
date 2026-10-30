-- Doanh thu theo mức thu nhập; hộ không có nhân khẩu học gộp vào 'Unknown', không bị rơi mất.
WITH hh_revenue AS (
    SELECT household_key, sum(SALES_VALUE) AS revenue
    FROM transaction_data
    WHERE SALES_VALUE > 0 AND QUANTITY > 0
    GROUP BY 1
)
SELECT coalesce(d.INCOME_DESC, 'Unknown') AS income_desc,
       count(*) AS households,
       round(sum(r.revenue), 2) AS revenue,
       round(sum(r.revenue) / sum(sum(r.revenue)) OVER (), 4) AS share
FROM hh_revenue r
LEFT JOIN hh_demographic d USING (household_key)    -- INNER JOIN sẽ bỏ 68% số hộ
GROUP BY 1
ORDER BY revenue DESC
