-- Doanh thu của mỗi danh mục: own_revenue (trực tiếp) và total_revenue (gồm mọi con cháu).
-- Cột: category_id, name, own_revenue, total_revenue
-- TODO: tính own_revenue, dựng closure (ancestor, descendant) bằng WITH RECURSIVE, rồi cộng dồn
SELECT category_id, name, 0 AS own_revenue, 0 AS total_revenue
FROM categories
ORDER BY category_id
