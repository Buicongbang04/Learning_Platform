---
title: Dịch vụ sản phẩm polyglot với MongoDB và Redis
level: advanced
services: [mongo, redis]
files:
  - path: starter/service.py
    note: 7 TODO
  - path: tests/test_product_service.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/03-nosql/exercises/advanced/01-product-service-polyglot -q
  - docker compose -f setup/docker-compose.yml up -d mongo redis
  - uv run pytest tracks/data-engineer/modules/03-nosql/exercises/advanced/01-product-service-polyglot -q
---

## Mục tiêu

Ghép các kỹ năng của module thành một dịch vụ nhỏ giống thật: MongoDB là nguồn sự thật cho sản phẩm và review,
Redis làm cache, leaderboard, danh sách "vừa xem" và rate limiter. Bạn tự quyết định cách giữ dữ liệu nhất quán
giữa hai store, xử lý ghi lặp (idempotency), cache stampede và cold start. Đây là phần lõi của capstone m03.

## Đề bài

Hoàn thiện lớp `ProductService(db, r, clock=time.time, min_reviews=3, rate_limit=5, rate_window=60)` trong
`starter/service.py`. `db` là database pymongo (collection `products`, `reviews`), `r` là client Redis với
`decode_responses=True`, `clock()` trả thời gian hiện tại tính bằng giây.

Document sản phẩm: `{"_id": product_id, "category": str, "price": float}`; service tự thêm các trường tính sẵn
`review_count`, `score_sum`, `avg_score`.

1. `get_product(product_id)`: cache-aside với key `product:<id>`, TTL khoảng 300 giây (cho phép cộng jitter
   tối đa 60 giây). Chống cache stampede bằng một lock trong Redis: chỉ request giữ lock mới nạp lại cache.
   Sản phẩm không tồn tại trả `None`.
2. `add_review(review)`: review có `review_id`, `product_id`, `score` (1–5), `created_at`. Ghi vào `reviews`
   (với `_id = review_id`) và cập nhật các trường tính sẵn của sản phẩm **bằng toán tử nguyên tử**, không
   read-modify-write. Gửi lại cùng `review_id` không được đếm hai lần. Trả `True` nếu là review mới. Sau khi ghi,
   lần `get_product` kế tiếp phải thấy số liệu mới.
3. `top_rated(k=10)`: list `(product_id, avg_score)` điểm cao trước, chỉ gồm sản phẩm có ít nhất `min_reviews`
   review, đọc từ sorted set Redis `top_rated`. Nếu Redis mất dữ liệu (key không tồn tại) thì dựng lại từ
   MongoDB rồi trả kết quả.
4. `record_view(user_id, product_id)` và `recently_viewed(user_id)`: tối đa 10 sản phẩm vừa xem, mới nhất trước,
   không trùng lặp.
5. `allow_request(client_id)`: sliding window, tối đa `rate_limit` request mỗi `rate_window` giây.

Ngoài code, viết một đoạn ngắn ở đầu `service.py` (docstring) giải thích: thứ tự ghi Mongo/Redis bạn chọn, điều
gì xảy ra nếu Redis chết giữa chừng, và giới hạn còn lại của thiết kế.

## Tiêu chí đạt

- Test offline (mongomock + fakeredis) pass.
- Khi bật `mongo` và `redis`, test chạy trên dịch vụ thật cũng pass (dùng database/khoá riêng, tự dọn).
- Không có read-modify-write cho bộ đếm review; review lặp không làm sai số liệu.
- Mất toàn bộ dữ liệu Redis không làm mất dữ liệu nghiệp vụ: mọi kết quả dựng lại được từ MongoDB.
- Docstring giải thích được các đánh đổi về consistency.

## Gợi ý

### Gợi ý 1

Idempotent: `insert_one` với `_id = review_id` và bắt `DuplicateKeyError`; chỉ khi insert thành công mới
`$inc` bộ đếm. `avg_score` có thể cập nhật bằng aggregation pipeline update
(`update_one(filter, [{"$set": ...}])`) hoặc tính từ `score_sum / review_count` sau `find_one_and_update` với
`return_document=ReturnDocument.AFTER`.

### Gợi ý 2

Lock: `r.set(f"lock:product:{id}", token, nx=True, ex=5)`. Không lấy được lock thì đọc thẳng Mongo (hoặc chờ ngắn
rồi đọc cache). "Vừa xem": `LREM` rồi `LPUSH` rồi `LTRIM 0 9` trong một pipeline. Cold start của leaderboard: quét
`products` có `review_count >= min_reviews` rồi `ZADD` hàng loạt.
