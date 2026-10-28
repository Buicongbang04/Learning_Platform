---
title: Gợi ý "mua cùng" bằng graph và Cypher
level: basic
services: [neo4j]
files:
  - path: starter/graph.py
    note: 5 TODO
  - path: tests/test_copurchase.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/03-nosql/exercises/basic/03-neo4j-copurchase -q
  - docker compose -f setup/docker-compose.yml up -d neo4j
  - uv run pytest tracks/data-engineer/modules/03-nosql/exercises/basic/03-neo4j-copurchase -q
---

## Mục tiêu

Thấy vì sao bài toán "khách mua X cũng mua gì" tự nhiên trên graph: mô hình `(:Customer)-[:BOUGHT]->(:Product)`,
nạp dữ liệu idempotent bằng `MERGE`, và truy vấn hai bước bằng Cypher. Bạn viết cùng logic bằng Python thuần để
so sánh. Phần Python và phần kiểm tra tĩnh câu Cypher chạy offline; phần chạy trên Neo4j thật tự skip nếu chưa
bật dịch vụ.

## Đề bài

Dữ liệu đầu vào là danh sách lượt mua (rút gọn từ `orders` + `order_items` của Olist):

```python
{"customer_id": "c1", "order_id": "o1", "product_id": "p1", "category": "housewares"}
```

Hoàn thiện `starter/graph.py`:

1. `co_purchase_counts(purchases, product_id, k=5)` (Python thuần): với các khách đã mua `product_id`, đếm mỗi
   sản phẩm **khác** được bao nhiêu khách **khác nhau** mua. Trả list tuple `(product_id, n_customers)` sắp theo
   `n_customers` giảm dần rồi `product_id` tăng dần, tối đa `k` phần tử.
2. `CONSTRAINTS`: list câu Cypher tạo unique constraint cho `Customer.id` và `Product.id` (dùng `IF NOT EXISTS`).
3. `LOAD_QUERY`: một câu Cypher nhận tham số `$rows` (list dict như trên), dùng `UNWIND` và `MERGE` để tạo node
   `Customer {id}`, `Product {id, category}` và quan hệ `BOUGHT {order_id}`. Chạy lại nhiều lần không tạo trùng.
4. `COPURCHASE_QUERY`: nhận `$pid` và `$k`, trả hai cột `product_id` và `customers` với cùng ý nghĩa và thứ tự
   như hàm Python ở bước 1.
5. `load_purchases(driver, rows)` và `co_purchase(driver, product_id, k)`: chạy các câu trên bằng
   `driver.execute_query`; `co_purchase` trả list tuple giống bước 1.

## Tiêu chí đạt

- `co_purchase_counts` đúng với dữ liệu mẫu, không tính chính sản phẩm đầu vào, đếm khách distinct.
- `LOAD_QUERY` dùng `UNWIND $rows` và `MERGE`, không dùng `CREATE` cho node/quan hệ.
- `COPURCHASE_QUERY` dùng `$pid`, `$k` và quan hệ `BOUGHT`.
- Khi Neo4j chạy: nạp hai lần vẫn đúng số node/quan hệ, và kết quả Cypher bằng kết quả Python.

## Gợi ý

### Gợi ý 1

Python: dựng `dict customer -> set(product)`, lấy tập khách đã mua `product_id`, rồi dùng `Counter` trên các
sản phẩm khác của họ (mỗi khách góp tối đa 1 cho mỗi sản phẩm vì là `set`).

### Gợi ý 2

Cypher:

```cypher
MATCH (:Product {id: $pid})<-[:BOUGHT]-(c:Customer)-[:BOUGHT]->(o:Product)
WHERE o.id <> $pid
RETURN o.id AS product_id, count(DISTINCT c) AS customers
ORDER BY customers DESC, product_id ASC
LIMIT $k
```

Constraint: `CREATE CONSTRAINT customer_id IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE`.
