---
title: CRUD, truy vấn và index cho review Olist trên MongoDB
level: basic
services: []
files:
  - path: starter/reviews.py
    note: 5 TODO
  - path: tests/test_mongo_reviews.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/03-nosql/exercises/basic/01-mongo-reviews-crud -q
---

## Mục tiêu

Làm quen với API `pymongo`: ghi idempotent bằng upsert, lọc bằng toán tử truy vấn (`$lte`, `$in`), projection,
sort, cập nhật một phần bằng `$set`/`$inc`, và tạo compound index theo quy tắc ESR. Test chạy offline bằng
`mongomock` (giả lập MongoDB trong bộ nhớ), code của bạn chạy y hệt với MongoDB thật.

## Đề bài

Mỗi review Olist là một dict:

```python
{"review_id": "r1", "order_id": "o1", "product_id": "p1", "score": 5,
 "comment": "chegou rapido", "created_at": datetime(2018, 3, 1, 10, 0)}
```

Hoàn thiện các hàm trong `starter/reviews.py`. Mọi hàm nhận `db` là một `Database` của pymongo (hoặc mongomock)
và làm việc trên collection `reviews`.

1. `load_reviews(db, reviews)`: ghi danh sách review, dùng `review_id` làm `_id` (không lưu trường
   `review_id` riêng). Phải **idempotent**: chạy hai lần với cùng dữ liệu không tạo bản trùng, chạy lại với
   dữ liệu đã sửa thì ghi đè. Trả về tổng số document trong collection sau khi ghi.
2. `low_score_reviews(db, max_score=2)`: trả về list dict `{"review_id", "order_id", "score"}` của các review
   có `score <= max_score`, sắp theo `score` tăng dần rồi `review_id` tăng dần. Dùng projection, không trả
   `comment`.
3. `reviews_for_product(db, product_id, limit=10)`: các review của một sản phẩm, mới nhất trước
   (`created_at` giảm dần), tối đa `limit` document, giữ nguyên các trường như trong DB.
4. `answer_review(db, review_id, answer)`: đặt `answer` và `answered = True` cho review, đồng thời tăng
   `answer_count` thêm 1 (trường chưa có thì coi như 0). Trả về `True` nếu tìm thấy review, ngược lại `False`.
5. `create_indexes(db)`: tạo compound index phục vụ truy vấn ở bước 3 và trả về tên index.

## Tiêu chí đạt

- Gọi `load_reviews` hai lần trên cùng dữ liệu, collection vẫn có đúng số review.
- Document lưu `_id` bằng `review_id` và không có trường `review_id`.
- `low_score_reviews` trả đúng tập, đúng thứ tự, đúng ba khoá.
- `reviews_for_product` trả mới nhất trước và tôn trọng `limit`.
- `answer_review` cập nhật một phần (không làm mất `comment`), `answer_count` tăng dần qua mỗi lần gọi.
- `create_indexes` tạo index có key `[("product_id", 1), ("created_at", -1)]`.

## Gợi ý

### Gợi ý 1

Idempotent = `replace_one({"_id": ...}, doc, upsert=True)` cho từng review, hoặc `bulk_write` với các
`ReplaceOne(..., upsert=True)`. `count_documents({})` đếm tổng.

### Gợi ý 2

`find(filter, projection).sort([("score", 1), ("_id", 1)])`; projection `{"_id": 1, "order_id": 1, "score": 1}`
rồi đổi `_id` thành `review_id` trong Python. Cập nhật một phần dùng
`update_one({"_id": id}, {"$set": {...}, "$inc": {"answer_count": 1}})` và kiểm tra `matched_count`.
`create_index([("product_id", ASCENDING), ("created_at", DESCENDING)])` trả về tên index.
