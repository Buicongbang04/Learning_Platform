-- Pareto / phân nhóm ABC mặt hàng theo doanh thu, 12 tháng 12/2010 - 11/2011.
WITH by_product AS (
    SELECT stock_code, sum(quantity * price) AS revenue
    FROM online_retail
    WHERE invoice NOT LIKE 'C%' AND quantity > 0 AND price > 0
      AND regexp_matches(stock_code, '^[0-9]{5}')
      AND invoice_date >= DATE '2010-12-01' AND invoice_date < DATE '2011-12-01'
    GROUP BY 1
),
cum AS (
    SELECT stock_code, revenue,
           row_number() OVER w AS rnk,
           -- ROWS: luỹ kế đúng từng dòng kể cả khi hai mặt hàng bằng doanh thu
           sum(revenue) OVER (w ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running,
           sum(revenue) OVER () AS total
    FROM by_product
    WINDOW w AS (ORDER BY revenue DESC, stock_code)
)
SELECT stock_code, round(revenue, 2) AS revenue, rnk, round(running / total, 4) AS cum_share,
       CASE WHEN (running - revenue) / total < 0.80 THEN 'A'   -- luỹ kế TRƯỚC mặt hàng này
            WHEN (running - revenue) / total < 0.95 THEN 'B'
            ELSE 'C' END AS abc_class
FROM cum
ORDER BY rnk
