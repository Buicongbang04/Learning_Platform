-- Top 3 mặt hàng theo doanh thu ở mỗi nước, 12 tháng 12/2010 - 11/2011, chỉ hàng hoá.
WITH sales AS (
    SELECT country, stock_code, quantity * price AS revenue
    FROM online_retail
    WHERE invoice NOT LIKE 'C%' AND quantity > 0 AND price > 0
      AND regexp_matches(stock_code, '^[0-9]{5}')                       -- hàng hoá; bỏ POST, DOT, M, ...
      AND invoice_date >= DATE '2010-12-01' AND invoice_date < DATE '2011-12-01'   -- khoảng nửa mở
),
by_product AS (
    SELECT country, stock_code, sum(revenue) AS revenue
    FROM sales
    GROUP BY 1, 2
),
ranked AS (
    SELECT *,
           row_number() OVER (PARTITION BY country ORDER BY revenue DESC, stock_code) AS rnk,
           revenue / sum(revenue) OVER (PARTITION BY country) AS share   -- tính TRƯỚC khi lọc top 3
    FROM by_product
)
SELECT country, rnk, stock_code, round(revenue, 2) AS revenue, round(share, 4) AS share_of_country
FROM ranked
WHERE rnk <= 3
ORDER BY country, rnk
