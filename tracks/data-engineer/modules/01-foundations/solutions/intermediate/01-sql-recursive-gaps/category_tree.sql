-- Cây danh mục: category_id, name, depth, path, sắp theo path.
WITH RECURSIVE tree AS (
    -- anchor: các danh mục gốc
    SELECT category_id, name, 0 AS depth, CAST(name AS VARCHAR) AS path
    FROM categories
    WHERE parent_id IS NULL
    UNION ALL
    -- recursive: con của các dòng vừa sinh ở vòng trước
    SELECT c.category_id, c.name, t.depth + 1, t.path || ' > ' || c.name
    FROM categories c
    JOIN tree t ON c.parent_id = t.category_id
    WHERE t.depth < 50          -- chốt chặn nếu dữ liệu lỡ có chu trình
)
SELECT category_id, name, depth, path
FROM tree
ORDER BY path
