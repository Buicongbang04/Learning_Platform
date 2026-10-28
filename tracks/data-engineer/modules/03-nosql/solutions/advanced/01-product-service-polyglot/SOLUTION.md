# Hướng làm: dịch vụ sản phẩm polyglot với MongoDB và Redis

Bài này không có một đáp án duy nhất. Dưới đây là một hướng làm đã kiểm chứng với bộ test, các quyết định cần
cân nhắc và rubric chấm.

## Nguyên tắc nền

- **MongoDB là nguồn sự thật**, Redis chỉ chứa dữ liệu *dẫn xuất* (cache, leaderboard, danh sách vừa xem, bộ
  đếm rate limit). Mất Redis thì chậm đi, không mất nghiệp vụ.
- **Ghi Mongo trước, rồi mới động tới Redis** (xoá cache, cập nhật leaderboard). Ghi Mongo lỗi thì dừng, Redis vẫn
  phản ánh trạng thái cũ hợp lệ. Redis lỗi sau khi Mongo đã ghi thì cache cũ tồn tại tối đa tới hết TTL, và
  leaderboard có thể lệch — cần một job đối soát (rebuild định kỳ từ Mongo) hoặc CDC (change stream) để sửa.

## Từng phần

### `get_product`

```python
cached = r.get(key)
if cached is not None: return decode(cached)
token = uuid4().hex
have_lock = r.set(f"lock:{key}", token, nx=True, ex=5)
doc = db.products.find_one({"_id": pid})
if have_lock:
    r.set(key, json.dumps(doc, default=str), ex=300 + random.randint(0, 60))   # hoặc "__none__" với TTL ngắn
    if r.get(f"lock:{key}") == token: r.delete(f"lock:{key}")                 # chỉ xoá lock của mình
return doc
```

- Lock `SET NX EX` đảm bảo khi key nóng hết hạn chỉ một request ghi lại cache; `EX` để lock tự nhả nếu process
  chết. So token trước khi xoá để không xoá nhầm lock của request khác (lý tưởng là Lua script để so-và-xoá nguyên
  tử).
- Request không có lock có thể đọc Mongo trực tiếp (như trên), hoặc chờ vài chục ms rồi đọc lại cache — đánh đổi
  giữa tải DB và độ trễ.
- Jitter cho TTL để hàng nghìn key nạp cùng lúc không hết hạn cùng lúc.

### `add_review`

1. `insert_one({"_id": review_id, ...})`, bắt `DuplicateKeyError` → trả `False`. Đây là chốt idempotency: unique
   `_id` do database đảm bảo, không phải `if exists then insert` (có race).
2. Chỉ khi insert thành công: `find_one_and_update({"_id": pid}, {"$inc": {"review_count": 1, "score_sum": s}},
   return_document=AFTER)`. `$inc` là nguyên tử trên document, nhiều review đồng thời không mất cập nhật.
3. `avg_score`: tính từ `score_sum / review_count` của document trả về rồi `$set`, hoặc tốt hơn trên MongoDB thật là
   **pipeline update** trong một lệnh:
   `update_one({"_id": pid}, [{"$set": {"review_count": {"$add": [{"$ifNull": ["$review_count", 0]}, 1]}, ...}},
   {"$set": {"avg_score": {"$divide": ["$score_sum", "$review_count"]}}}])`.
4. Xoá cache `product:<pid>`, nếu `review_count >= min_reviews` thì `ZADD top_rated pid avg`.

Khoảng hở còn lại: nếu process chết giữa bước 1 và 2, review đã có nhưng bộ đếm chưa tăng, và lần gửi lại sẽ bị coi
là trùng. Cách khắc phục: dùng **multi-document transaction** (Mongo replica set) cho bước 1–2, hoặc không lưu bộ
đếm mà tính lại định kỳ bằng aggregation, hoặc job đối soát `count(reviews) vs review_count`.

### `top_rated`

Đọc `ZREVRANGE top_rated 0 k-1 WITHSCORES`. Nếu key không tồn tại (Redis restart, bị evict), dựng lại từ
`products` có `review_count >= min_reviews` rồi `ZADD` hàng loạt. Chú ý phân biệt "key không tồn tại" và
"leaderboard rỗng thật" — có thể đặt một key đánh dấu `top_rated:built`.

### `record_view` / `recently_viewed`

Pipeline `LREM key 0 pid` → `LPUSH key pid` → `LTRIM key 0 9` → `EXPIRE`. Danh sách luôn ≤ 10 phần tử, không trùng,
mới nhất ở đầu. Thêm TTL (vd. 30 ngày) để user không quay lại không chiếm RAM mãi.

### `allow_request`

Sliding window log bằng sorted set (`ZREMRANGEBYSCORE`, `ZCARD`, `ZADD`, `EXPIRE`), thời gian lấy từ `self.clock()`
để test được. Member phải duy nhất cho mỗi request (`uuid4`), nếu dùng timestamp làm member thì hai request cùng
thời điểm bị gộp. Production: Lua script để nguyên tử.

## Quyết định thiết kế nên nêu trong docstring

| Quyết định | Lựa chọn | Đánh đổi |
| --- | --- | --- |
| Invalidate hay update cache khi ghi | Xoá | Một lần miss sau mỗi ghi, nhưng tránh ghi đè sai thứ tự |
| Bộ đếm review | Lưu sẵn (computed pattern) | Đọc nhanh, nhưng cần đối soát; thay thế là aggregate khi đọc |
| Leaderboard | Redis sorted set dẫn xuất | Có thể lệch nếu Redis lỗi giữa chừng; rebuild được |
| Lock stampede | `SET NX EX` + token | Không phải Redlock; đủ cho một instance Redis |
| Consistency | Eventual giữa Mongo và Redis, cửa sổ ≤ TTL | Trang sản phẩm có thể chậm vài giây so với review mới |

## Rubric (100 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Test offline pass (mongomock + fakeredis) | 25 |
| Test với dịch vụ thật pass (`mongo`, `redis`) | 10 |
| Idempotency review dựa trên unique key của DB, không read-modify-write cho bộ đếm | 15 |
| Cache-aside đúng: ghi DB trước rồi xoá cache; TTL có jitter; negative caching hoặc xử lý `None` hợp lý | 10 |
| Chống stampede bằng lock có TTL, không xoá nhầm lock | 10 |
| Leaderboard dựng lại được từ Mongo; mọi dữ liệu Redis đều là dẫn xuất | 10 |
| Rate limiter đúng, member duy nhất, có TTL; nêu được race và cách sửa bằng Lua | 5 |
| Docstring giải thích thứ tự ghi, hỏng hóc giữa chừng, giới hạn còn lại | 10 |
| Code rõ ràng: tên key nhất quán (có namespace), không hard-code thời gian, pipeline để giảm round-trip | 5 |

Mức đạt: từ 70 điểm và hai mục đầu không bị 0.
