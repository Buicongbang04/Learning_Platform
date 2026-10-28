-- Doanh thu của mỗi danh mục: own_revenue (trực tiếp) và total_revenue (gồm mọi con cháu).
WITH RECURSIVE own AS (
    SELECT c.category_id, c.name, COALESCE(SUM(oi.price), 0) AS own_revenue
    FROM categories c
    LEFT JOIN products p ON p.category_id = c.category_id
    LEFT JOIN order_items oi ON oi.product_id = p.product_id
    GROUP BY c.category_id, c.name
),
closure AS (
    -- mỗi danh mục là con cháu của chính nó
    SELECT category_id AS ancestor_id, category_id AS descendant_id, 0 AS depth
    FROM categories
    UNION ALL
    -- thêm con trực tiếp của descendant hiện tại
    SELECT cl.ancestor_id, c.category_id, cl.depth + 1
    FROM closure cl
    JOIN categories c ON c.parent_id = cl.descendant_id
    WHERE cl.depth < 50
)
SELECT
    o.category_id,
    o.name,
    o.own_revenue,
    SUM(d.own_revenue) AS total_revenue
FROM own o
JOIN closure cl ON cl.ancestor_id = o.category_id
JOIN own d ON d.category_id = cl.descendant_id
GROUP BY o.category_id, o.name, o.own_revenue
ORDER BY o.category_id
