# M03: Cache sản phẩm bằng Redis, review vào MongoDB

## Mục tiêu

Chọn đúng kho NoSQL cho đúng bài toán: Redis làm cache đọc nhanh thông tin sản phẩm (pattern
cache-aside), MongoDB lưu review dạng document để tìm kiếm và tổng hợp linh hoạt.

## Việc cần làm

1. Bật dịch vụ:

   ```bash
   docker compose -f setup/docker-compose.yml up -d postgres redis mongo
   ```

2. **Redis cache-aside** – `project/ingestion/product_cache.py`:
   - Hàm `get_product(product_id)`: đọc `product:{id}` (Redis hash) → nếu miss thì query
     `dw.dim_product` trên Postgres, ghi vào Redis với TTL 1 giờ, trả kết quả.
   - Hàm `invalidate(product_id)`.
   - Đếm hit/miss bằng `INCR cache:hit` / `cache:miss`.
   - Thêm sorted set `top_products:revenue` (score = doanh thu) để lấy top 10 bằng `ZREVRANGE`.
3. **MongoDB reviews** – `project/ingestion/load_reviews_mongo.py`:
   - Nạp `olist_order_reviews_dataset.csv` vào `olist.reviews`, mỗi document nhúng (embed)
     thông tin tóm tắt đơn (`order_status`, `customer_state`) và danh sách `product_category`.
   - Upsert theo `review_id` (idempotent).
   - Tạo index: `{review_score: 1}`, `{"order.customer_state": 1}`, text index trên
     `review_comment_message`.
   - Viết aggregation pipeline: điểm trung bình và số review theo danh mục; tỉ lệ review trống.
4. Test không cần Docker trong `project/tests/test_nosql.py` bằng `fakeredis` và `mongomock`.
5. Đo: thời gian 1000 lần `get_product` khi cache lạnh và khi cache nóng.
6. Chạy:

   ```bash
   uv run python tracks/data-engineer/capstone/project/ingestion/load_reviews_mongo.py --data-dir data/raw
   uv run python tracks/data-engineer/capstone/project/ingestion/product_cache.py --benchmark 1000
   uv run pytest tracks/data-engineer/capstone/project/tests -q
   ```

## Kết quả nộp

- `product_cache.py`, `load_reviews_mongo.py`, `test_nosql.py`
- Mục "NoSQL decisions" trong `project/README.md`: vì sao embed thay vì reference, vì sao chọn
  TTL đó, kết quả benchmark lạnh/nóng.

## Tiêu chí đạt

- [ ] Lần gọi thứ hai cho cùng `product_id` không truy vấn Postgres (kiểm bằng counter hoặc mock).
- [ ] Key Redis có TTL (`TTL product:<id>` > 0).
- [ ] Chạy lại script Mongo không tăng số document.
- [ ] Aggregation theo danh mục trả kết quả khớp truy vấn SQL tương đương trên `dw`.
- [ ] Review có `review_comment_message` trống được lưu đúng (không bị bỏ, không thành chuỗi `"nan"`).
- [ ] Test chạy pass không cần bật Docker.
