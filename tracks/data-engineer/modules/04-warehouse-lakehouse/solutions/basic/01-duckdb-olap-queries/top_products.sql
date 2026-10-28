WITH product_revenue AS (
    SELECT
        p.product_category_name AS category,
        i.product_id,
        SUM(i.price) AS revenue
    FROM order_items AS i
    JOIN orders AS o USING (order_id)
    JOIN products AS p USING (product_id)
    WHERE o.order_status = 'delivered'
    GROUP BY 1, 2
)
SELECT
    category,
    product_id,
    revenue,
    ROW_NUMBER() OVER (PARTITION BY category ORDER BY revenue DESC, product_id) AS rnk
FROM product_revenue
QUALIFY rnk <= 2
ORDER BY category, rnk
