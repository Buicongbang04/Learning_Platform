---
title: Embedding đơn hàng Olist và aggregation pipeline
level: intermediate
services: []
files:
  - path: starter/pipelines.py
    note: 4 TODO
  - path: tests/test_mongo_aggregation.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/03-nosql/exercises/intermediate/01-mongo-aggregation -q
---

## Mục tiêu

Chuyển dữ liệu quan hệ (orders, order_items, products) thành document lồng theo access pattern
(embedding + extended reference), rồi viết aggregation pipeline cho các câu hỏi phân tích: doanh thu theo
category, đơn và GMV theo tháng, điểm review trung bình theo sản phẩm có `$lookup`. Test chạy offline bằng
`mongomock`.

## Đề bài

Hoàn thiện `starter/pipelines.py`:

1. `build_order_documents(orders, items, products)` nhận ba list dict kiểu bảng quan hệ:
   - `orders`: `order_id, customer_id, customer_state, order_status, purchased_at` (datetime)
   - `items`: `order_id, order_item_id, product_id, seller_id, price, freight_value`
   - `products`: `product_id, category`

   Trả về list document, mỗi đơn một document:

   ```python
   {"_id": "o1",
    "customer": {"id": "c1", "state": "SP"},
    "status": "delivered",
    "purchased_at": datetime(...),
    "items": [  # sắp theo order_item_id
        {"product_id": "p1", "seller_id": "s1", "category": "housewares", "price": 10.0, "freight": 2.5}],
    "total": 12.5}  # tổng price + freight, làm tròn 2 chữ số
   ```

   Đơn không có item thì `items = []`, `total = 0.0`. Sản phẩm không có trong `products` thì `category = None`.
2. `revenue_by_category_pipeline(status="delivered")`: pipeline trên collection `orders` (document ở bước 1).
   Chỉ tính đơn có `status` bằng tham số. Trả document `{"category", "revenue", "items"}` với `revenue` = tổng
   `price` (không gồm freight), `items` = số dòng item; sắp `revenue` giảm dần. Không có `_id` trong kết quả.
3. `monthly_orders_pipeline()`: theo tháng mua (`"YYYY-MM"`), trả `{"month", "orders", "gmv"}` với `gmv` = tổng
   `total`; sắp `month` tăng dần, không có `_id`.
4. `product_rating_pipeline(min_reviews=2)`: pipeline trên collection `reviews`
   (`{_id, product_id, score}`) và `$lookup` sang collection `products` (`{_id: product_id, category}`). Trả
   `{"product_id", "category", "avg_score", "n_reviews"}` cho sản phẩm có ít nhất `min_reviews` review, sắp
   `avg_score` giảm dần rồi `product_id` tăng dần, không có `_id`.

Lưu ý: `mongomock` chưa hỗ trợ `$round`; hãy để làm tròn cho phía Python (test so sánh gần đúng).

## Tiêu chí đạt

- Document đơn hàng đúng cấu trúc, item đúng thứ tự, `category` được chép sang item (extended reference).
- Ba pipeline là `list[dict]` hợp lệ, chạy được bằng `collection.aggregate(...)` và cho đúng kết quả.
- Không còn khoá `_id` trong kết quả pipeline.
- Pipeline doanh thu lọc trạng thái bằng `$match` ở **stage đầu tiên**.

## Gợi ý

### Gợi ý 1

`build_order_documents`: dựng dict `product_id -> category` và `order_id -> [items]` trước, tránh vòng lặp lồng
O(n*m). Thứ tự stage cho doanh thu: `$match` → `$unwind: "$items"` → `$group` → `$project` → `$sort`.

### Gợi ý 2

Tháng: `{"$dateToString": {"format": "%Y-%m", "date": "$purchased_at"}}` làm `_id` của `$group`.
Rating: `$group` theo `$product_id` với `$avg`/`$sum: 1`, `$match` theo số review, rồi
`$lookup {from: "products", localField: "_id", foreignField: "_id", as: "product"}`, `$unwind: "$product"`,
`$project` lấy `"$product.category"`.
