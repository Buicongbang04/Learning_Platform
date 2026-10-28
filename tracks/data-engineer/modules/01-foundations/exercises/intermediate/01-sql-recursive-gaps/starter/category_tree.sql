-- Cây danh mục: category_id, name, depth, path (vd. 'Casa > Moveis > Moveis Sala'), sắp theo path.
-- TODO: WITH RECURSIVE, anchor là các gốc (parent_id IS NULL), bước đệ quy nối con vào cha
SELECT category_id, name, 0 AS depth, name AS path
FROM categories
ORDER BY path
