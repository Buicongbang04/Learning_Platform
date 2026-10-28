# Lời giải: CRUD, truy vấn và index cho review Olist

## Cách làm

- **`load_reviews`**: dùng `review_id` làm `_id` để MongoDB tự đảm bảo duy nhất, rồi
  `replace_one({"_id": id}, doc, upsert=True)`. Upsert theo khoá tự nhiên là cách chuẩn để một job nạp dữ liệu
  chạy lại bao nhiêu lần cũng ra cùng kết quả (idempotent). `insert_many` sẽ lỗi `DuplicateKeyError` ở lần chạy
  thứ hai. Với khối lượng lớn, gom thành `bulk_write([ReplaceOne(...), ...], ordered=False)` để giảm round-trip.
- **`low_score_reviews`**: filter `{"score": {"$lte": max_score}}`, projection chỉ lấy trường cần (giảm dữ liệu
  qua mạng), sort hai khoá để kết quả xác định. Không sort thì MongoDB trả theo thứ tự tự nhiên, không ổn định.
- **`reviews_for_product`**: `find(...).sort("created_at", -1).limit(n)`. Có index ở bước 5 thì MongoDB đọc
  thẳng theo thứ tự index, dừng sau `n` document, không phải sort trong bộ nhớ.
- **`answer_review`**: một lệnh `update_one` kết hợp `$set` và `$inc` là nguyên tử trên một document. Không đọc
  document về, sửa trong Python rồi ghi lại (read-modify-write) vì hai request đồng thời sẽ ghi đè nhau.
  `$inc` trên trường chưa có sẽ tạo trường với giá trị bằng số tăng. `matched_count` (chứ không phải
  `modified_count`) cho biết review có tồn tại.
- **`create_indexes`**: theo ESR, trường so sánh bằng (`product_id`) trước, trường sort (`created_at` giảm dần)
  sau. Tên index mặc định là `product_id_1_created_at_-1`.

## Kiểm chứng trên MongoDB thật

```python
from pymongo import MongoClient
db = MongoClient("mongodb://localhost:27017").olist
print(db.reviews.find({"product_id": "p1"}).sort("created_at", -1).limit(10).explain()["queryPlanner"]["winningPlan"])
```

Kế hoạch tốt có `IXSCAN` trên `product_id_1_created_at_-1` và không có stage `SORT`.
